# Phase 2.6 Implementation Report: Field Projection

**Date**: 2025-10-12  
**Version**: 0.5.0 → 0.5.1 (unreleased tag)

---

## Executive Summary

Phase 2.6 introduces Firestore field projection to FireProx via a new `.select()` API that mirrors the native Firestore query builder while preserving FireProx ergonomics. The feature works across the synchronous and asynchronous stacks, enabling developers to retrieve lightweight dictionary payloads containing only the fields they need. Projections automatically convert Firestore document references back into FireProx objects so that relationships remain intuitive even when partial documents are fetched.

---

## Key Deliverables

- ✅ Added `.select()` projection support to `FireQuery` and `AsyncFireQuery`, including chaining with existing query operations.
- ✅ Added `.select()` helper on `FireCollection` / `AsyncFireCollection` to bootstrap projected queries directly from a collection.
- ✅ Extended query execution methods (`get`, `get_all`, and `stream`) to return vanilla dictionaries when a projection is active while preserving FireObject conversion semantics for document references.
- ✅ Ensured projected results convert any nested `DocumentReference` values into FireObject/AsyncFireObject instances for seamless navigation.
- ✅ Added parity helper methods (`get_all`) on query classes to expose the projected iterator pattern consistently.

---

## Technical Highlights

1. **Immutable Projection Tracking**  
   Projection state rides along each chained query instance via an internal `_projection` tuple. All query-builder methods reuse this tuple, guaranteeing consistent results regardless of chaining order (`collection.select(...).where(...)` and `collection.where(...).select(...)` both work).

2. **Shared Conversion Logic**  
   Projection dictionaries reuse `BaseFireObject._convert_snapshot_value_for_retrieval` so nested references, vectors, and container types remain compatible with the rest of the FireProx ecosystem.

3. **API Parity**  
   New `get_all()` on query objects mirrors `FireCollection.get_all()` semantics, allowing projected reads to stream large result sets without full hydration.

4. **Async Symmetry**  
   Async implementations pass along the companion sync client (when available) so projected reference fields still benefit from lazy-loading and caching.

---

## Testing

- ✅ Added three synchronous projection tests covering `get`, `stream`, and `get_all` behaviours.  
- ✅ Added three asynchronous projection tests mirroring the synchronous scenarios.  
- ✅ Full test suite runs through the Firestore emulator to validate end-to-end behaviour.

---

## Documentation & Demos

- ✅ Updated both `STATUS.md` trackers with the new Phase 2.6 milestone and refreshed test counts.  
- ✅ Authored this implementation report detailing the feature set and architecture.  
- ✅ Added a new demo notebook, *Select Projections*, showcasing practical projection recipes for both sync and async APIs.  
- ✅ Updated `mkdocs.yml` navigation so the new demo surfaces in the docs site alongside existing topic demos.

---

## Follow-Up Opportunities

- 🔄 Extend projections to support aliasing/FieldPath renaming helpers for ergonomics.  
- 🔄 Investigate adding typed result helpers (e.g., dataclass hydration) layered on top of projected dictionaries.  
- 🔄 Explore projection-aware caching so repeated partial reads can reuse hydrated data when re-fetching full documents.
