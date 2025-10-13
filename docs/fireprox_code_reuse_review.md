# FireProx Sync/Async Architecture Review

## Current Design Strengths
- The project already centralizes substantial shared behavior in `BaseFireObject`, including state management, dirty tracking, conversion helpers, and transaction/batch utilities, which keeps lifecycle bookkeeping consistent for both sync and async variants.【F:src/fire_prox/base_fire_object.py†L17-L177】【F:src/fire_prox/base_fire_object.py†L414-L575】
- `BaseFireCollection` and `BaseFireProx` handle client bookkeeping, transaction/batch helpers, and path validation so that concrete sync/async classes focus on I/O-specific pieces.【F:src/fire_prox/base_fire_collection.py†L11-L153】【F:src/fire_prox/base_fireprox.py†L11-L263】

## Duplication Hotspots
### Attribute Hydration & Lazy Loading
- Both `FireObject.__getattr__` and `AsyncFireObject.__getattr__` repeat nearly identical conversion logic for vectors, document references, lists, and dicts, differing mainly in whether they spawn sync or async proxies.【F:src/fire_prox/fire_object.py†L57-L139】【F:src/fire_prox/async_fire_object.py†L57-L144】
- The conversion responsibilities already live in `_convert_snapshot_value_for_retrieval` and `_convert_value_for_storage` on the base class, so pushing more of the attribute-materialization logic into the base could avoid the duplication and ensure consistency between lazy-loaded attributes and values populated during `fetch()`/`from_snapshot()`.【F:src/fire_prox/base_fire_object.py†L538-L575】【F:src/fire_prox/base_fire_object.py†L671-L738】【F:src/fire_prox/base_fire_object.py†L740-L799】

### Fetch Flow
- Sync and async `fetch()` implementations share the same structure: state validation, optional transaction, conversion of snapshot data, and transition to `LOADED`. Only the snapshot retrieval differs (`get()` vs `await get()`).【F:src/fire_prox/fire_object.py†L148-L215】【F:src/fire_prox/async_fire_object.py†L150-L209】
- A template method on the base class could accept an injected callable/coroutine for performing the actual Firestore read, centralizing the conversion and state transition logic alongside `_transition_to_loaded`.

### Save Logic
- The `save()` methods repeat validation of DETACHED/DELETED states, doc reference creation, update-dict assembly for dirty fields, and shared calls to `_prepare_data_for_storage`/`_mark_clean`. The only differences are whether Firestore methods are awaited.【F:src/fire_prox/fire_object.py†L217-L362】【F:src/fire_prox/async_fire_object.py†L211-L335】【F:src/fire_prox/base_fire_object.py†L538-L575】【F:src/fire_prox/base_fire_object.py†L562-L575】
- Extracting helpers such as `_ensure_doc_ref(doc_id)` and `_apply_updates(update_dict, transaction, batch)` on the base class (with small sync/async overrides for the Firestore calls) would remove most duplicated control flow.

### Delete Logic
- `delete()` in both variants performs the same state checks and chooses between batch vs direct deletion before transitioning to `DELETED`. Only the actual delete call requires awaiting.【F:src/fire_prox/fire_object.py†L364-L407】【F:src/fire_prox/async_fire_object.py†L337-L373】【F:src/fire_prox/base_fire_object.py†L562-L579】
- A base helper that executes validation and state transitions while delegating the actual delete call to the subclass would further unify behavior.

### Collection Factories
- `FireCollection.new/doc` and `AsyncFireCollection.new/doc` contain mirrored logic for instantiating object proxies, differing only in whether sync companions are supplied.【F:src/fire_prox/fire_collection.py†L51-L99】【F:src/fire_prox/async_fire_collection.py†L47-L103】
- `BaseFireObject.collection()` currently inspects class names to decide whether to return sync or async collections, indicating that responsibility could move into dedicated overrides or shared factory utilities to avoid runtime heuristics.【F:src/fire_prox/base_fire_object.py†L218-L266】

### Root Client Interfaces
- `FireProx.doc/collection` and `AsyncFireProx.doc/collection` share the same validation, reference construction, and wrapper instantiation flow, aside from creating the companion sync client for async use.【F:src/fire_prox/fireprox.py†L102-L200】【F:src/fire_prox/async_fireprox.py†L98-L197】【F:src/fire_prox/base_fireprox.py†L204-L239】
- Introducing base-level helpers such as `_make_doc_ref(path)` and `_wrap_collection(collection_ref, **kwargs)` would allow the sync/async subclasses to override only the parts that actually differ (e.g., provisioning `_sync_client`).

## Suggested Refactor Direction
1. **Template Method for Fetch/Save/Delete**: Add protected async-aware helpers on `BaseFireObject` that encapsulate shared control flow (state checks, conversion, dirty tracking) while accepting lightweight hooks for the actual Firestore operations. Subclasses would then only supply the sync vs async I/O implementations.
2. **Shared Attribute Materialization**: Provide a `_get_field_value(name)` helper in the base class that handles lazy loading (invoking a subclass-supplied fetch hook) and value conversion via `_convert_snapshot_value_for_retrieval`. The sync/async classes would mainly define how to perform the actual fetch (synchronous call vs awaited coroutine).
3. **Factory Utilities for Collections/Docs**: Move repeated construction logic for `new()`/`doc()` on collections and for `doc()`/`collection()` on the root clients into shared helpers, with parameters for async-specific collaborators like `_sync_client`.
4. **Explicit Overrides Instead of Runtime Heuristics**: Replace the string-based async detection in `BaseFireObject.collection()` with explicit overrides on `FireObject` and `AsyncFireObject`, making the async companion wiring clearer and easier to extend.

## Risk & Testing Considerations
- Because the duplicated blocks are heavily exercised by the existing integration suite (sync + async), extracting shared helpers should be accompanied by regression runs of the full test harness to ensure transaction, batch, and lazy-loading semantics remain intact.
- Introducing template methods must respect coroutine semantics; designing hooks that can be awaited when necessary (e.g., returning awaitables or using `asyncio.iscoroutine`) will be important to avoid mixing sync/async code paths incorrectly.

## Recommended Next Steps
1. Prototype a `BaseFireObject._fetch_internal(get_snapshot)` helper and migrate both implementations to it, followed by similar extractions for `save()` and `delete()`.
2. Introduce shared attribute materialization helper(s) and update both `__getattr__` methods to call into them, verifying no regressions in lazy loading.
3. Split the subcollection factory logic into explicit overrides on the concrete classes to eliminate runtime type checks.
4. Refactor collection and client factory methods to rely on shared constructors, minimizing duplication when adding new flags/features in the future.
