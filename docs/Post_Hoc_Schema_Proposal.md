# Post-Hoc Schema Support Proposal

## Background

Fire-Prox today treats Firestore documents as schemaless payloads that are surfaced
as mutable Python objects. This keeps the prototyping experience fast, but makes it
difficult to opt-in to stronger typing, validation, and IDE assistance once a
collection stabilizes. Teams have asked for a way to declare a schema _after_ a
collection already exists without sacrificing Fire-Prox's dynamic ergonomics.

This document proposes an additive design that allows developers to register a
schema for any collection while preserving the current opt-in behavior and
minimizing churn across the synchronous and asynchronous APIs.

## Design Goals

1. **Opt-in by collection** – A schema should only apply when a user explicitly
   associates one with a collection. Existing code paths must continue to work
   unchanged when no schema is supplied.
2. **Adapter-based schema input** – Support data classes, lightweight classes with
   type annotations, and other plain Python instances without forcing a specific
   modeling framework.
3. **IDE-friendly types** – When a schema is registered, code completion and
   static analysis should understand document attributes.
4. **Runtime validation** – Provide configurable hooks to validate documents at
   creation, update, and fetch time. Defaults should be conservative to avoid
   surprising users.
5. **Minimal class explosion** – Favor generics and composition over new
   subclasses to prevent duplicating the Fire-Prox surface area.
6. **Extensible marshalling** – Allow registration of serializers for commonly
   requested immutable Python types (e.g., tuples, enums, timedeltas).

## Non-Goals

- Enforcing schemas at the Firestore level; this remains an application-level
  construct.
- Requiring PyDantic or any heavyweight validation library.
- Breaking the existing lazy-loading, mutation, or state-machine semantics of
  `FireObject` or `AsyncFireObject`.

## Key Concepts

### Schema Adapter Protocol

Introduce a lightweight `SchemaAdapter` protocol responsible for mapping between
Fire-Prox documents and user-defined schema containers. An adapter instance must
answer four questions:

- **`supports(obj_or_type)`** – Determine if the adapter can represent the
  provided schema definition (e.g., data class type, plain class type, callable
  factory).
- **`create_instance(data: Mapping[str, Any]) -> SchemaInstance`** – Produce a
  typed object from raw document data.
- **`to_mapping(instance) -> MutableMapping[str, Any]`** – Convert a typed object
  back to Firestore-friendly primitives.
- **`iter_fields(type_or_instance)`** – Yield `(name, field_info)` metadata,
  including type annotations and whether the field is a Fire-Prox reserved field
  (such as document path or timestamps).

The initial release would ship with built-in adapters for:

- Standard library `@dataclass` types.
- Plain classes that expose type annotations via `__annotations__` and can be
  constructed with keyword arguments.
- A fallback adapter that accepts dictionaries (current behavior).

Adapters are registered via a global registry similar to Python's `functools.singledispatch`.
Users can also register project-specific adapters (e.g., for attrs classes or
lightweight Pydantic models) without modifying Fire-Prox internals.

### Collection-Level Schema Binding

Extend `FireCollection` and `AsyncFireCollection` to accept an optional
`schema` argument when instantiated or via a fluent method:

```python
users = db.collection("users").with_schema(UserProfile)
```

Internally the collection caches a `SchemaBinding` object containing the chosen
adapter, the schema type, and configuration flags (validation level, custom
marshallers). The binding is propagated to newly created objects from that
collection.

### Generic Collection and Object Types

Parameterize the public classes with covariant type variables to retain static
information without introducing parallel class hierarchies:

```python
T_co = TypeVar("T_co", covariant=True)

class FireCollection(Generic[T_co]):
    schema: SchemaBinding[T_co] | None

class FireObject(Generic[T_co]):
    schema_instance: T_co | None
```

When no schema is supplied, `T_co` defaults to `Mapping[str, Any]`, preserving
existing type signatures. The async counterparts mirror this arrangement.

### Document Lifecycle

1. **Creation** – `collection.new()` returns a `FireObject[T_co]`. If a schema is
   bound, the object exposes a `schema_instance` attribute initialized via the
   adapter's factory (empty defaults). Assignment to document fields can either
   mutate the backing dictionary or operate on the schema object directly (see
   "Mutation Modes" below).
2. **Fetching** – When `fetch()` populates data, the binding uses
   `create_instance` to construct the typed object. Optional validation runs at
   this stage.
3. **Saving** – Before persistence, `to_mapping` normalizes the schema instance,
   merging Fire-Prox reserved metadata and applying custom marshallers.

### Mutation Modes

Provide two ergonomic patterns:

- **Schema-first**: Developers mutate the `schema_instance` and then call
  `save()`. Fire-Prox tracks dirty fields by comparing serialized mappings.
- **Dynamic fallback**: Direct attribute access on the `FireObject` (current
  behavior) remains available. In schema-bound collections, attribute writes are
  forwarded to the schema instance when possible and mirrored into the backing
  dictionary. This keeps legacy code functioning.

### Validation Options

`SchemaBinding` exposes configuration like `validate_on` with values in
`{"save", "fetch", "never", "always"}`. Validation uses adapter-provided hooks or
plain callable validators. The default is `validate_on={"save"}` to catch issues
before persistence without penalizing reads.

Errors raise `SchemaValidationError` with actionable messages and the offending
field paths.

### Document References via Annotated Types

Adapters interpret `typing.Annotated` metadata to distinguish Firestore document
references from embedded data. Example:

```python
from typing import Annotated

class Order(BaseModel):
    customer: Annotated[CustomerRef, "fire_prox.DocumentReference"]
```

The annotation tag instructs the adapter to serialize `customer` as a Firestore
reference (or `firestore.AsyncDocumentReference` in async contexts). Fire-Prox
can ship helper aliases like `fire_prox.annotations.DocRef[Customer]` to reduce
stringly-typed metadata while staying decoupled from any one modeling framework.

### Reserved Fields and Metadata

Fire-Prox-managed attributes (e.g., `id`, `path`, `snapshot`, timestamps) remain
available on the `FireObject`. The schema adapter can mark fields as "reserved"
so they are excluded from persistence but still populated on the schema instance
for convenience. This allows models to include read-only properties corresponding
to Firestore metadata while keeping write operations safe.

### Marshalling Strategy

Introduce a `MarshallerRegistry` with default handlers for:

- `enum.Enum`: stored as either name or value (configurable per field).
- `datetime.timedelta`: serialized to ISO 8601 duration strings or integer
  microseconds.
- `tuple`: converted to lists on write and back to tuples on read if flagged via
  annotations.

Collections inherit marshaller configuration from the parent `FireProx` instance
but can override per binding. Marshalled types integrate with validation so that
schema fields can remain strongly typed even though Firestore stores primitive
representations.

### Async Parity

`AsyncFireCollection` and `AsyncFireObject` share the same schema binding logic.
Adapters should remain synchronous; serialization and validation happen before
I/O. Async-specific code only handles awaiting Firestore operations, keeping the
feature surface consistent across both APIs.

## Migration and Compatibility

- **Default Behavior** – If users ignore the new API, Fire-Prox behaves exactly
  as before. Types default to `Mapping[str, Any]`, and no adapters or validators
  run.
- **Incremental Adoption** – Teams can gradually adopt schemas collection by
  collection. The adapter registry approach keeps per-project customization
  localized.
- **Testing Strategy** – New unit tests focus on adapter conversions,
  validation hooks, and marshaller registration. Integration tests cover sync
  and async flows with annotated references and reserved fields.

## Open Questions

1. **Schema inference for legacy data** – Should Fire-Prox offer utilities to
   infer a schema from existing documents, or is manual declaration sufficient?
2. **Partial updates** – How should `fire_object.save(fields=[...])` behave when
   using schema instances? We may need adapter support for sparse serialization.
3. **Performance considerations** – Large documents may incur overhead when
   serializing through adapters. Caching strategies or incremental diffing may be
   required.
4. **IDE integration** – We rely on generics to surface types, but verifying the
   experience across major editors (PyCharm, VS Code) warrants prototyping.

## Next Steps

1. Prototype the `SchemaAdapter` protocol and registry with dataclass support.
2. Implement collection binding and generic type propagation for the synchronous
   API, then mirror for the async API.
3. Design validation and marshalling configuration objects, including sensible
   defaults.
4. Author developer documentation with migration guides and examples.
5. Solicit feedback from early adopters before finalizing the API surface.

This proposal provides a path to post-hoc schema enforcement without sacrificing
Fire-Prox's prototyping strengths or demanding wholesale rewrites of existing
applications.
