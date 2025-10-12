# Phase 4 Projection Support Implementation Report

## Summary

This iteration adds Firestore projection support to FireProx's query stack. Both the synchronous and asynchronous query builders now expose a `.select()` method that mirrors the native Firestore API while returning FireProx-friendly payloads. Projected query results surface as vanilla dictionaries, but embedded document references continue to hydrate into FireObject or AsyncFireObject instances so that downstream code keeps the ergonomic FireProx experience.

## Key Enhancements

- Added `.select()` to `FireQuery` and `AsyncFireQuery`, carrying projection state through all query modifiers (`where`, `order_by`, cursors, etc.).
- Returned query payloads honour projection settings across `get()`, `stream()`, and the new `get_all()` alias, emitting dictionaries with recursively converted reference fields.
- Extended `FireCollection` and `AsyncFireCollection` with convenience `.select()` factories while documenting how to chain projections into `get_all()` calls.
- Ensured async projections can still lazily resolve referenced documents by threading the companion sync client through conversion utilities.

## Testing

Comprehensive unit coverage now exercises sync and async projection flows:

- `.select().get()` returns dictionaries limited to requested fields.
- `.select().stream()` and `.select().get_all()` behave identically for projections.
- Document reference fields within projected results convert back into FireProx objects for both APIs.

All new scenarios run against the Firestore emulator inside the existing pytest harness.

## Documentation & Demos

- Added a demo notebook (`demos/topics/select_projections.ipynb`) demonstrating projection workflows for both sync and async clients.
- Updated the MkDocs navigation to surface the new topic notebook.
- Refreshed `STATUS.md` with the latest feature milestone and test totals.

## Next Steps

Future work can expand projections with helper utilities (e.g., projection presets) and integration into higher-level query helpers once the roadmap advances into broader Phase 4 features.
