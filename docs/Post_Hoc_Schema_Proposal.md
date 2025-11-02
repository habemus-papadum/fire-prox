# Post-Hoc Schema Support Proposal

## Background

Fire-Prox today treats Firestore documents as schemaless payloads that are surfaced
as mutable Python objects. This keeps the prototyping experience fast, but makes it
difficult to opt-in to stronger typing and IDE assistance once a collection
stabilizes. Teams have asked for a way to declare a schema _after_ a collection
already exists without sacrificing Fire-Prox's dynamic ergonomics or changing
runtime behavior.

This document proposes an additive design that allows developers to register a
schema for any collection while preserving the current opt-in behavior and
minimizing churn across the synchronous and asynchronous APIs.

## Design Goals

1. **Opt-in by collection** – A schema should only apply when a user explicitly
   associates one with a collection. Existing code paths must continue to work
   unchanged when no schema is supplied.
2. **Dataclass-first schema input** – Limit phase-one support to standard
   library `@dataclass` definitions with type annotations. This keeps
   expectations clear while leaving room for other sources in future work.
3. **IDE-friendly types** – When a schema is registered, code completion and
   static analysis should understand document attributes while still recognizing
   Fire-Prox lifecycle methods such as `save()` and `delete()`.
4. **Zero runtime impact** – Schema metadata must not change the runtime behavior
   of Fire-Prox. Users may still assign undeclared fields or values that do not
   match annotations; the goal is purely improved static analysis.
5. **Minimal class explosion** – Favor generics and composition over new
   subclasses to prevent duplicating the Fire-Prox surface area.

## Non-Goals

- Enforcing schemas at the Firestore level; this remains an application-level
  construct.
- Requiring PyDantic or any heavyweight validation library.
- Changing runtime mutation rules, error handling, or attribute semantics of
  `FireObject` or `AsyncFireObject`.
- Breaking the existing lazy-loading, mutation, or state-machine semantics of
  `FireObject` or `AsyncFireObject`.

## Key Concepts

### Dataclass Schema Introspection

Phase one focuses exclusively on Python `@dataclass` types. Fire-Prox will
introspect the dataclass fields and annotations to learn which document
attributes exist, their expected types, and which of them should be surfaced as
document references (see below). The dataclass is **not** instantiated or
validated at runtime; the information is used only to build typing metadata that
editors and linters can consume.

Future phases may expand support to other container types, but limiting the
scope to dataclasses keeps the implementation predictable and avoids premature
abstraction layers such as adapter registries.

### Collection-Level Schema Binding

Extend `FireCollection` and `AsyncFireCollection` to accept an optional
`schema` argument when instantiated. This keeps the call site concise while
maintaining backwards compatibility:

```python
users: FireCollection = db.collection("users", UserProfile)
```

Passing a schema at instantiation should work the same way for nested
collections:

```python
orders: FireCollection = user.collection("orders", Order)
```

Internally the collection caches lightweight metadata that captures the chosen
dataclass type and derived field annotations. No validation or marshalling
configuration is performed in this phase. The binding is propagated to newly
created objects from that collection. When no schema is supplied—e.g.,
`db.collection("users")`—the behavior is identical to today's Fire-Prox API.

### Generic Collection and Object Types

Parameterize the public classes with covariant type variables to retain static
information without introducing parallel class hierarchies:

```python
T_co = TypeVar("T_co", covariant=True)

class FireCollection(Generic[T_co]):
    schema: type[T_co] | None

class FireObject(Generic[T_co]):
    schema_type: type[T_co] | None
```

When no schema is supplied, `T_co` defaults to `types.SimpleNamespace` so that
attribute access continues to feel natural while staying loose enough for the
dynamic prototyping story. The async counterparts mirror this arrangement. For
static analysis we prefer modeling `FireObject[T]` itself as a structural
extension of `T`, keeping a standalone alias like
`TypedFireObject[T] = FireObject[T] & T` unnecessary. Tooling should instead see
`FireObject[T]` (and the async equivalent) as providing both Fire-Prox lifecycle
methods (e.g., `save`, `delete`, `fetch`) and the dataclass fields without
raising spurious warnings.

### Example Usage

```python
@dataclass
class UserProfile:
    display_name: str
    age: int


@dataclass
class Order:
    purchaser: FireObject[UserProfile]  # FireObject already surfaces the schema
    total: float


users: FireCollection = db.collection("users", UserProfile)
orders: FireCollection = db.collection("orders", Order)

ada = users.doc("ada")  # linter should see this as a UserProfile
order_doc = orders.new()  # linter should see this as an Order
user_orders: FireCollection = ada.collection("orders", Order)
# Docs obtained from queries should also work the same way

order_doc.purchaser = ada
order_doc.total = 199.00
order_doc.save()  # linter should not complain when using FireObject methods
```

Calling `db.collection("users")` without a schema argument remains fully
supported, preserving the existing dynamic ergonomics.

### Query Type Propagation

Queries created from a typed collection (e.g., `collection.where(...)` or
`collection.order_by(...)`) should preserve the same generic parameter, allowing
linters and IDEs to infer the document type for fetched results. Projected
queries (those using `select`/`projection` APIs where fields are expressed as
strings) will remain untyped for now because determining the resulting shape is a
larger design effort. Aggregate queries (e.g., `count`, `sum`) may expose return
types via generic parameters tied to the aggregate operation since their output
contracts are well-defined.

### Document Lifecycle

1. **Creation** – `collection.new()` returns a `FireObject[T_co]`. If a schema is
   bound, the object records the `schema_type` so that type checkers can treat
   the value as both a `FireObject` and the provided dataclass. Assignment to
   document fields continues to behave exactly as it does today.
2. **Fetching** – When `fetch()` populates data, runtime objects remain the same
   mutable Fire-Prox wrappers. No dataclass instance is constructed unless a
   future phase opts into that behavior. Static type information remains
   available regardless of fetch state.
3. **Saving** – Persistence uses the existing code paths. Schema metadata is
   advisory only and does not block writes or coerce data.

### Mutation Modes

Provide two ergonomic patterns:

- **Typed view**: Static type checkers see a `FireObject` that is also
  compatible with the dataclass schema. This means methods such as `.save()` or
  `.delete()` remain visible to the linter while dataclass fields surface for
  attribute completion without needing an additional alias.
- **Dynamic fallback**: Direct attribute access on the `FireObject` (current
  behavior) remains available. Attribute writes are not blocked or validated
  against schema metadata.

### Async Parity

`AsyncFireCollection` and `AsyncFireObject` share the same schema binding logic.
Schema metadata extraction remains synchronous; runtime serialization continues
to rely on existing Fire-Prox behavior. Async-specific code only handles
awaiting Firestore operations, keeping the feature surface consistent across
both APIs.

## Migration and Compatibility

- **Default Behavior** – If users ignore the new API, Fire-Prox behaves exactly
  as before. Types default to `types.SimpleNamespace`, and no additional
  metadata processing occurs.
- **Incremental Adoption** – Teams can gradually adopt schemas collection by
  collection. Dataclass declarations live alongside existing code and do not
  require framework-specific registries.
- **Testing Strategy** – Static analysis test fixtures (see below) confirm that
  type hints propagate correctly without changing runtime semantics.

## Open Questions

1. **Schema inference for legacy data** – Should Fire-Prox offer utilities to
   infer a schema from existing documents, or is manual declaration sufficient?
2. **Partial updates** – How should `fire_object.save(fields=[...])` behave when
   schema hints are present? We may eventually need helper utilities for sparse
   serialization.
3. **IDE integration** – We rely on generics to surface types, but verifying the
   experience across major editors (PyCharm, VS Code) warrants prototyping.

## Next Steps

1. Prototype the dataclass introspection helpers and verify they capture field
   types and metadata needed for generics.
2. Implement collection binding and generic type propagation for the synchronous
   API, then mirror for the async API.
3. Author developer documentation with migration guides and examples.
4. Solicit feedback from early adopters before finalizing the API surface.

This proposal provides a path to post-hoc schema typing without sacrificing
Fire-Prox's prototyping strengths or demanding wholesale rewrites of existing
applications.

## Testing Strategy

Because the runtime behavior is unchanged, automated testing focuses on static
analysis. The proposed approach is:

1. **Type-fixture modules** – Add small Python modules under `tests/static_typing`
   that instantiate typed collections, execute queries (excluding projections),
   and call lifecycle methods such as `save()`/`delete()`. These modules do not
   run during normal test execution.
2. **Linter/Type-checker run** – Integrate `pyright` or `mypy` (in strict mode)
   into CI to analyze the fixture modules. Successful runs confirm that type
   information propagates and no unexpected errors are reported.
3. **Negative fixtures** – Provide companion modules that intentionally misuse
   types (e.g., assigning the wrong type to an annotated field). The type
   checker should emit diagnostics for these files, ensuring the typing signals
   are visible to developers.

These tests exercise the static contracts without requiring the Firebase
emulator or altering runtime execution paths.

## Typing Infrastructure Considerations

- Favor `.pyi` type stubs to express the generic relationships and overload
  behaviors described above. Retrofitting the runtime modules with complex
  annotations risks destabilizing the implementation, whereas dedicated stubs
  can model richer typing logic without touching production code.
- Expect to ship new or updated stubs for the `fire_prox` package alongside the
  feature. Without `.pyi` files encoding the overloads for `collection()` and
  subcollection helpers, static type checkers are unlikely to infer the desired
  shapes; it is almost certain the proposal will fall short without them, and
  feasibility still needs to be validated once the stubs exist.
- Use runtime annotations only where they remain simple and maintainable;
  anything more elaborate should live exclusively in the stub files, even if the
  approach requires experimentation to verify feasibility.

## Implementation Plan

1. **Dataclass schema analysis**
    - Implement utilities that inspect dataclass field annotations and convert
      them into Fire-Prox typing metadata.
2. **Schema binding on collections**
   - Extend `FireCollection` and `AsyncFireCollection` to accept a schema and
     store the dataclass type alongside derived metadata.
   - Ensure new objects and fetch operations expose the schema type while leaving
     runtime mutation unchanged.
3. **Generic type propagation**
   - Parameterize collection, object, and query classes with covariant type
     variables.
   - Propagate generics through query builders (excluding projections) and
     aggregates so that result types remain discoverable by type checkers.
4. **Documentation and developer experience**
    - Update docstrings and guides with examples of registering schemas and
      running static type checks.
5. **Static analysis test harness**
   - Add the type-fixture modules and configure CI to run `pyright`/`mypy`
     against them, capturing both positive and negative cases.
6. **Type stub publication**
   - Author `.pyi` files (or extend existing ones) that encode the collection
     overloads, generic propagation, and FireObject behaviors needed for
     checkers to understand the new surface area without complicating the
     runtime modules.

## Future Work

Potential follow-up enhancements include runtime validation hooks, marshaller
registries for complex types, schema-aware partial updates, and richer IDE
integrations once the foundational typing infrastructure lands.
