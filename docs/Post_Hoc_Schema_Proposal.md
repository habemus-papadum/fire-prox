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
4. **Linter-first enforcement** – The primary purpose of the schema system is to
   improve editor and static-analysis feedback without changing runtime
   semantics. Validation hooks remain opt-in for teams that explicitly request
   them.
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

### Critique of the Current Proposal

While the adapter-based design provides a solid foundation, it leaves several
notable gaps when weighed against the goal of lightweight typing support:

- **Query ergonomics** – The proposal does not describe how typed schemas flow
  into queries, projections, or aggregations, leaving IDEs unaware of the shape
  of query results.
- **Sentinel handling** – Firestore "magic" values such as
  `firestore.SERVER_TIMESTAMP` are not addressed. Without explicit treatment,
  adapters cannot surface accurate static types or retain runtime behavior.
- **Partial payloads** – Real-world documents frequently contain extra fields or
  missing keys. The proposal hints at validation but does not clarify how the
  typing story tolerates incomplete instances without raising runtime errors.
- **Static tooling emphasis** – Validation is positioned as a headline feature,
  which risks implying runtime failures. Given that the immediate need is IDE
  feedback, the document should de-emphasize validation and show how typing is
  preserved even when validation is disabled.
- **Interplay with dynamic access** – The hybrid mutation model is promising but
  needs clearer guarantees about how dynamic `fire_object["field"]` access and
  typed attributes coexist, especially when data returned from queries omits
  fields.

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

To keep the feature linter-first, Fire-Prox should default to
`validate_on={"never"}` and supply guardrails via static types. Teams can opt in
to stronger guarantees incrementally.

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

### Query and Aggregation Typing

Typed schemas should extend beyond individual document fetches. The binding can
participate in query construction by:

- Propagating the `T_co` type variable onto `Query` objects returned by
  `collection.where(...)`, `collection.limit(...)`, and similar methods. This
  allows `for doc in query.stream()` loops to expose typed `FireObject[T_co]`
  instances to the IDE.
- Supporting projections (`select`, `select_fields`) by introducing a
  `TypedProjection[T_partial]` helper. The helper can interpret a field subset
  and synthesize a `TypedDict` or `Protocol` representing the returned shape.
  Adapters provide a `project(fields)` method that returns the narrowed type.
- Ensuring aggregation results carry type metadata. For example,
  `collection.aggregate(count="id")` could return a `TypedDict` describing the
  expected keys while allowing adapters to enrich known numeric return types.
- Allowing custom query operators to request adapter metadata (e.g., field
  aliases or converters) to keep runtime behavior aligned with static analysis.

### Sentinel and Server Timestamp Support

Firestore exposes sentinel values such as `firestore.SERVER_TIMESTAMP` that are
commonly applied during `set`/`update`. To keep static typing accurate while
preserving runtime semantics:

- Adapters should expose a `sentinels` mapping from schema fields to known
  Firestore sentinel factories. Annotated fields can opt into sentinel behavior
  via helper markers like `fire_prox.annotations.ServerTimestamp`. During
  serialization the adapter substitutes the sentinel; when data is fetched the
  field resolves to `datetime.datetime | None` while retaining IDE awareness of
  the dual type.
- `SchemaBinding` tracks fields that accept sentinels to prevent linter errors
  when code assigns the sentinel constant. This ensures that `user.updated_at =
  firestore.SERVER_TIMESTAMP` type-checks even when the schema declares the
  field as `datetime.datetime`.
- Query projections should recognize sentinel fields and mark them as optional
  when the Firestore server has not yet populated the value.

### Partial and Evolving Payloads

To align with Fire-Prox's schemaless roots while enabling typing:

- Adapters must tolerate missing or extra fields. `create_instance` should
  populate default values when possible and surface unknown fields through a
  dedicated `extras` attribute (e.g., `Mapping[str, Any]`) that developers can
  inspect without breaking static types.
- `SchemaBinding` can expose a `strict=False` flag that keeps runtime operations
  permissive but provides a configuration knob for future tightening.
- Dynamic attribute access should fall back to the underlying dictionary even
  when the field is not part of the schema. IDEs can model this via a
  `Protocol` that includes `__getitem__` returning `Any` alongside typed
  attributes.

### Static Tooling Integration

To fulfill the linter-first focus:

- Provide `typing_extensions.Protocol` definitions for `FireObject[T_co]` and
  query iterables so tools like mypy, pyright, and Ruff's checker understand the
  API surface.
- Ship stub files (`.pyi`) that mirror runtime modules but include the generic
  annotations and projection helpers. Stubs allow editors to offer completions
  even before runtime implementations are complete.
- Offer mypy and pyright plugins that can read schema registrations from source
  code, enabling cross-module inference when collections are bound in one file
  but consumed elsewhere.

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
- **Tooling Samples** – Provide example configurations for mypy, pyright, and
  Ruff to demonstrate how typed collections surface actionable diagnostics.

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
5. **Server timestamp defaults** – Should sentinel-aware fields automatically
   mark themselves as optional in schemas, or do we require explicit typing like
   `datetime | None` to avoid confusion?
6. **Query result typing** – How far should Fire-Prox go in synthesizing
   `TypedDict`/`Protocol` types for projections without overwhelming users with
   complex generics?
7. **Static analysis scaling** – What heuristics are needed so linters do not
   re-run expensive adapter discovery on every import, especially in large
   codebases?

## Next Steps

1. Prototype the `SchemaAdapter` protocol and registry with dataclass support.
2. Implement collection binding and generic type propagation for the synchronous
   API, then mirror for the async API.
3. Design validation and marshalling configuration objects, including sensible
   defaults.
4. Extend query objects with generic typing and projection helpers, ensuring
   stubs and protocols compile under mypy and pyright.
5. Implement sentinel annotations and ensure runtime behavior mirrors Firestore
   semantics without introducing validation errors.
6. Author developer documentation with migration guides and examples emphasizing
   IDE usage and linter configuration.
7. Solicit feedback from early adopters before finalizing the API surface.

This proposal provides a path to post-hoc schema enforcement without sacrificing
Fire-Prox's prototyping strengths or demanding wholesale rewrites of existing
applications.
