# FireProx Logic Review

## Scope and Approach
This review covers the FireProx document, collection, and client entrypoint classes across the synchronous and asynchronous stacks. I focused on the shared base classes (`BaseFireObject`, `BaseFireCollection`, `BaseFireProx`) and their concrete sync/async implementations to evaluate code reuse and identify opportunities to consolidate duplicated logic without changing runtime behavior. Findings are based on the current repository state (no modifications applied) and on exploratory reading of the implementation.

## Current Architecture Snapshot
* **Shared foundations** – `BaseFireObject` centralizes state bookkeeping, dirty tracking, Firestore value conversion, and listener support for both sync and async objects, already reducing duplication for cross-cutting behaviors.【F:src/fire_prox/base_fire_object.py†L1-L738】 `BaseFireCollection` and `BaseFireProx` similarly hold common transaction/batch helpers, identity properties, and path validation.【F:src/fire_prox/base_fire_collection.py†L11-L200】【F:src/fire_prox/base_fireprox.py†L1-L260】
* **Sync vs async surfaces** – `FireObject`/`AsyncFireObject`, `FireCollection`/`AsyncFireCollection`, and `FireProx`/`AsyncFireProx` are responsible for all Firestore I/O because they must invoke either blocking or awaited client primitives.【F:src/fire_prox/fire_object.py†L102-L398】【F:src/fire_prox/async_fire_object.py†L98-L360】【F:src/fire_prox/fireprox.py†L102-L200】【F:src/fire_prox/async_fireprox.py†L98-L197】

## Duplication Hotspots
1. **Attribute materialization** – Both `FireObject.__getattr__` and `AsyncFireObject.__getattr__` perform nearly identical conversion chains (vector wrapping, reference hydration, list/dict recursion) after triggering their respective lazy load paths.【F:src/fire_prox/fire_object.py†L83-L138】【F:src/fire_prox/async_fire_object.py†L88-L142】 The only divergence is how the initial fetch happens (sync `fetch()` vs. sync client read inside async variant).
2. **Fetch logic** – The sync and async `fetch` methods share validation, snapshot-to-dict handling, and conversion to Python types before calling `_transition_to_loaded`. The difference is limited to how the snapshot is retrieved (awaited vs direct) and whether a sync companion client is injected.【F:src/fire_prox/fire_object.py†L200-L215】【F:src/fire_prox/async_fire_object.py†L200-L209】
3. **Save logic** – The largest duplication appears here: both implementations branch on DETACHED/ATTACHED/LOADED, enforce the same transaction/batch restrictions, build identical `update_dict` payloads for partial updates, and call `_prepare_data_for_storage` before writes.【F:src/fire_prox/fire_object.py†L217-L360】【F:src/fire_prox/async_fire_object.py†L211-L335】 Only the actual Firestore calls differ (awaited vs direct).
4. **Delete logic** – Both classes perform the same state validation and then call either `delete` or `await delete` before `_transition_to_deleted()`.【F:src/fire_prox/fire_object.py†L361-L398】【F:src/fire_prox/async_fire_object.py†L337-L360】
5. **Client and collection entry points** – `FireProx.collection/doc` and `AsyncFireProx.collection/doc` mirror each other aside from constructing sync companions for async use.【F:src/fire_prox/fireprox.py†L102-L200】【F:src/fire_prox/async_fireprox.py†L98-L197】 Likewise, `FireCollection.new/doc` and `AsyncFireCollection.new/doc` only differ in supplying async-specific references.【F:src/fire_prox/fire_collection.py†L34-L92】【F:src/fire_prox/async_fire_collection.py†L34-L82】

## Opportunities for Better Reuse
### 1. Template Methods for Document Lifecycle
*Introduce template hooks in `BaseFireObject` so the base class orchestrates state machine transitions while subclasses supply the minimal Firestore I/O primitives.*

Recommended hook surface:
* `_get_snapshot(transaction)` – returns a `DocumentSnapshot` (sync) or awaits one (async).
* `_create_document(doc_id)` – returns a new document reference tied to the correct client type.
* `_write_set(doc_ref, data, transaction=None, batch=None)` – handles full `set` operations.
* `_write_update(update_dict, transaction=None, batch=None)` – executes partial updates.
* `_write_delete(batch=None)` – deletes via the appropriate client.

With those in place, `BaseFireObject.fetch/save/delete` can be implemented once using the shared dirty-tracking utilities already in the base class, while subclasses override only the new hooks. This eliminates the repeated DETACHED/ATTACHED/LOADED branching and update payload construction currently duplicated across sync/async implementations.【F:src/fire_prox/fire_object.py†L217-L360】【F:src/fire_prox/async_fire_object.py†L211-L335】【F:src/fire_prox/base_fire_object.py†L500-L640】

### 2. Shared Attribute Materialization
`BaseFireObject` already exposes `_convert_snapshot_value_for_retrieval`, which mirrors the conversion logic hard-coded in each `__getattr__`. Exposing a helper like `_materialize_field(name)` that encapsulates conversion and caching would let both subclasses delegate after handling their specific lazy-load trigger. Each `__getattr__` would reduce to “ensure loaded, then return `_materialize_field(name)`”, avoiding the current duplication of vector/reference/list/dict handling.【F:src/fire_prox/fire_object.py†L83-L138】【F:src/fire_prox/async_fire_object.py†L88-L142】【F:src/fire_prox/base_fire_object.py†L640-L738】

### 3. Consolidate Entry-Point Factories
* Move shared path validation + reference creation scaffolding to the base classes.*
  * `BaseFireProx` could offer `_make_document(path)` / `_make_collection(path)` template methods that encapsulate `_validate_path` plus reference construction, with subclasses only responsible for returning the appropriate FireObject/Collection wrappers (and, in async, attaching the sync companion).【F:src/fire_prox/base_fireprox.py†L200-L239】【F:src/fire_prox/fireprox.py†L102-L200】【F:src/fire_prox/async_fireprox.py†L98-L197】
  * `BaseFireCollection` could expose `_instantiate_object(doc_ref, **kwargs)` so that sync/async variants simply pass context (e.g., sync companion refs) while the base handles parent wiring. This would eliminate repeated `State.DETACHED`/`State.ATTACHED` setup code in `new()`/`doc()`.【F:src/fire_prox/base_fire_collection.py†L26-L105】【F:src/fire_prox/fire_collection.py†L34-L92】【F:src/fire_prox/async_fire_collection.py†L34-L82】

### 4. Align Async Companion Client Handling
Currently async classes embed knowledge about when to create sync references (e.g., in `AsyncFireProx.__init__` and `AsyncFireCollection.doc`). Introducing a small utility on `AsyncFireProx` (or a mixin) to create paired async/sync references would prevent scattering `sync_client` plumbing across multiple call sites. That utility could be reused by both `AsyncFireObject` and `AsyncFireCollection` when spawning nested references.【F:src/fire_prox/async_fireprox.py†L84-L197】【F:src/fire_prox/async_fire_collection.py†L34-L82】

## Suggested Refactor Path
1. **Add hook interfaces** – Define abstract (or `NotImplementedError`) hook methods on `BaseFireObject` for snapshot retrieval and write operations. Update sync/async subclasses to implement them minimally.
2. **Port lifecycle logic to base** – Gradually move the shared parts of `fetch`, `save`, and `delete` into `BaseFireObject`, delegating to the new hooks for client calls. Retain subclass overrides temporarily while introducing unit tests to lock behavior, then delete the duplicated logic once parity is confirmed.
3. **Refine attribute access** – Extract `_materialize_field` in the base class and replace conversion blocks in both `__getattr__` methods with a call to it, leaving only the lazy-load trigger paths in subclasses.
4. **Generalize factory helpers** – Extend `BaseFireProx`/`BaseFireCollection` with helper constructors so sync/async implementations focus on context differences (e.g., providing sync companion references) instead of repeating state setup.
5. **Test coverage** – Ensure both sync and async integration suites continue to pass, paying special attention to lazy loading, transactions/batches, atomic operations, and nested reference conversion. Existing integration tests should catch regressions, but add targeted unit tests for the new base hooks if coverage is light.

## Risks and Mitigations
* **Async I/O nuances** – Centralizing logic must respect `await` requirements. Keeping the actual Firestore calls inside subclass hook implementations maintains control over coroutine boundaries.
* **State machine regressions** – Because DETACHED/ATTACHED/LOADED handling is critical, move logic incrementally and rely on exhaustive tests (sync + async) after each consolidation step.
* **Circular imports** – Introducing new helpers must avoid reintroducing circular dependencies (already managed by local imports inside methods). Continue to use local imports when instantiating sibling classes.

## Next Steps
* Prototype the hook-based refactor in a feature branch, running the full emulator-backed test suite after each migration step.
* Measure code reduction (lines and cyclomatic complexity) in `FireObject`/`AsyncFireObject` to ensure the consolidation meaningfully improves maintainability.
* Update developer documentation to reflect the new extension points once stabilized.

