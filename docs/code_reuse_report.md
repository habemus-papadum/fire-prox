# FireProx Key Class Code Reuse Review

## Scope and Approach
This review covers the document, collection, and root entry-point classes across the synchronous and asynchronous FireProx APIs. The focus is on `BaseFireObject`/`FireObject`/`AsyncFireObject`, `BaseFireCollection`/`FireCollection`/`AsyncFireCollection`, and `BaseFireProx`/`FireProx`/`AsyncFireProx`. I compared their responsibilities, looked for duplicated logic, and evaluated how much work already lives in the shared base layers. All observations below are grounded in the current code base.

## Existing Strengths
* The base classes already centralize state tracking, conversion helpers, and common metadata accessors (IDs, paths, repr/str), which keeps a large amount of shared behavior out of the concrete classes.【F:src/fire_prox/base_fire_object.py†L671-L738】【F:src/fire_prox/base_fire_collection.py†L20-L153】【F:src/fire_prox/base_fireprox.py†L20-L204】
* Factory helpers such as `_create_from_snapshot_base` ensure snapshot hydration is shared between sync and async objects, avoiding reimplementation of recursive conversion logic.【F:src/fire_prox/base_fire_object.py†L809-L842】
* Transaction and batch helpers are consistently provided at each layer through the base classes, so there is little duplication for those entry points.【F:src/fire_prox/base_fire_collection.py†L45-L105】【F:src/fire_prox/base_fireprox.py†L67-L204】

## Duplication Hotspots and Opportunities
### 1. Field materialization in `__getattr__`
Both concrete document classes reproduce the same branching logic to turn stored vectors and document references into rich wrapper objects during attribute access.【F:src/fire_prox/fire_object.py†L57-L139】【F:src/fire_prox/async_fire_object.py†L57-L142】 The base class already knows how to translate stored values through `_convert_value_for_storage` and `_convert_snapshot_value_for_retrieval`, but the concrete `__getattr__` implementations repeat that work. A shared helper such as `_materialize_field(name)` inside `BaseFireObject` could encapsulate the conversion rules while letting subclasses focus only on the lazy-load trigger (sync fetch versus sync-backed fetch for async).

### 2. Fetch pipelines
`FireObject.fetch` and `AsyncFireObject.fetch` both perform the same state checks, call Firestore, iterate over `snapshot.to_dict()`, and feed values through `_convert_snapshot_value_for_retrieval` before calling `_transition_to_loaded`.【F:src/fire_prox/fire_object.py†L150-L215】【F:src/fire_prox/async_fire_object.py†L150-L208】 The only divergence is how the snapshot is retrieved (awaitable vs. immediate). Extracting a template method in the base class—for example, `_fetch_snapshot(get_snapshot_callable)`—would remove the repeated conversion loop while preserving the different I/O mechanics via a subclass-supplied callable or coroutine.

### 3. Save/update branching
The synchronous and asynchronous `save` methods share the same three-way state machine (DETACHED creation, LOADED partial update, ATTACHED overwrite) and build identical payloads for partial updates, differing only in whether Firestore operations are awaited.【F:src/fire_prox/fire_object.py†L217-L362】【F:src/fire_prox/async_fire_object.py†L211-L335】 Introducing a base-layer workflow that returns a "write plan" (e.g., `{operation: 'create'|'update'|'set', payload: ...}`) would consolidate validation, payload construction, and state transitions. Each subclass would then only execute the plan through sync or async Firestore clients. This also opens the door to unit tests that cover the plan generation once, instead of twice.

### 4. Delete operations
Both concrete document classes implement identical deletion checks followed by either `doc_ref.delete()` or `await doc_ref.delete()` before calling `_transition_to_deleted()`.【F:src/fire_prox/fire_object.py†L364-L407】【F:src/fire_prox/async_fire_object.py†L337-L373】 A shared `_delete_document(executor)` helper in the base could accept a callable/awaitable and centralize validation and state mutation.

### 5. Collection factories
`FireCollection.new/doc` and `AsyncFireCollection.new/doc` are near-mirror implementations that only differ in the target class and whether a sync companion reference is created.【F:src/fire_prox/fire_collection.py†L51-L100】【F:src/fire_prox/async_fire_collection.py†L47-L103】 A base-level factory helper (e.g., `_build_document(self, *, doc_id=None, async_mode=False)`) or a mixin that receives the FireObject class and optional sync client would reduce duplication and make future state-machine tweaks propagate to both variants automatically.

### 6. Root `doc`/`collection` entry points
`FireProx.doc/collection` and `AsyncFireProx.doc/collection` repeat the same validation and wrapper creation logic with only minor differences for async (creating a companion sync client and passing it through).【F:src/fire_prox/fireprox.py†L102-L205】【F:src/fire_prox/async_fireprox.py†L98-L197】 A shared method in `BaseFireProx` that accepts the concrete FireObject/FireCollection classes and an optional sync-client factory could encapsulate the flow, leaving the subclasses responsible only for configuring the appropriate constructors.

## Recommended Refactor Plan
1. **Introduce base-level field access helper**  
   * Add `_materialize_field(name, value, *, is_async)` to `BaseFireObject` that reuses `_convert_snapshot_value_for_retrieval`/`_convert_value_for_storage` to turn stored primitives into wrapper instances. Subclasses can then reduce `__getattr__` to “trigger fetch if needed, then call base helper,” removing duplicated conversion rules.【F:src/fire_prox/fire_object.py†L57-L139】【F:src/fire_prox/async_fire_object.py†L57-L142】【F:src/fire_prox/base_fire_object.py†L671-L738】

2. **Template the fetch workflow**  
   * Move the shared post-fetch logic (state validation, conversion, `_transition_to_loaded`) into `BaseFireObject._load_from_snapshot(snapshot, *, sync_client=None)`.  
   * Have `FireObject.fetch` and `AsyncFireObject.fetch` focus solely on obtaining the snapshot (sync vs. awaitable) and then delegate to the base method, shrinking each implementation to a few lines.【F:src/fire_prox/fire_object.py†L150-L215】【F:src/fire_prox/async_fire_object.py†L150-L208】

3. **Centralize save planning**  
   * Create a base helper that, given the current state, returns an object describing the Firestore operation (create/update/set), the payload dictionary, and the target reference.  
   * Reuse the helper from both `save` methods to drive Firestore I/O, leaving only the actual `set/update`/`await` differences in the subclasses. This eliminates duplicated validation, payload construction, and dirty-tracking resets.【F:src/fire_prox/fire_object.py†L217-L362】【F:src/fire_prox/async_fire_object.py†L211-L335】

4. **Unify delete handling**  
   * Implement `_perform_delete(executor)` in the base class to run validation and call `_transition_to_deleted`. The executor can be either the synchronous delete call or an awaited coroutine, which keeps subclass implementations minimal.【F:src/fire_prox/fire_object.py†L364-L407】【F:src/fire_prox/async_fire_object.py†L337-L373】

5. **Factor collection/document factories**  
   * Add a protected builder in `BaseFireCollection` that takes the FireObject class, the document ID (optional), and the sync companion client. Both sync and async collections would then call into it, reducing duplication when we need to modify initialization parameters (e.g., future subcollection support).【F:src/fire_prox/fire_collection.py†L51-L100】【F:src/fire_prox/async_fire_collection.py†L47-L103】

6. **Share `doc`/`collection` wiring at the FireProx level**  
   * Expose helper methods in `BaseFireProx` that perform path validation, instantiate the right CollectionReference/DocumentReference objects, and call provided constructor callables. This keeps the subclasses focused on supplying constructors (and the async companion sync client) while ensuring behavior like path validation lives in exactly one place.【F:src/fire_prox/base_fireprox.py†L204-L260】【F:src/fire_prox/fireprox.py†L102-L205】【F:src/fire_prox/async_fireprox.py†L98-L197】

## Testing and Rollout Considerations
* Each refactor should be accompanied by the existing integration test suites (sync and async) to confirm that lazy loading, state transitions, and conversion behavior remain intact.  
* Where new base helpers are introduced, add unit tests that exercise the helpers directly to reduce reliance on end-to-end integration tests.  
* Because async code paths sometimes rely on companion synchronous clients (for lazy loading and listeners), ensure that any new base abstractions accept the optional sync client to avoid regressions in listener behavior.【F:src/fire_prox/async_fireprox.py†L86-L134】【F:src/fire_prox/async_fire_object.py†L57-L142】

Implementing the steps above would meaningfully reduce duplicated logic while keeping the sync and async APIs aligned, making future feature additions (like subcollections or additional atomic operations) easier to implement once and share everywhere.
