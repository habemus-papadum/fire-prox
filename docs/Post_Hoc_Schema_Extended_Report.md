# Post-Hoc Schema Support — Extended Plan

## Purpose

This report expands on the proposal for adding post-hoc schemas to Fire-Prox with
an emphasis on static typing and tooling. The goal is to describe how the system
should behave end to end so IDEs, linters, and type-checkers provide immediate
feedback when developers opt into schemas without breaking the dynamic runtime
experience that exists today.

## Guiding Principles

1. **Typing-first** – Schema metadata powers code completion, lints, and type
   checking. Runtime validation remains optional and opt-in.
2. **Runtime compatibility** – Existing collections and documents continue to work
   even when their stored data does not match the declared schema. Mismatches are
   surfaced through static tooling or explicitly enabled validation hooks.
3. **Incremental adoption** – Teams bind schemas collection by collection and can
   mix typed and untyped code paths inside the same application.
4. **Adapter extensibility** – The schema system understands dataclasses, plain
   classes, and custom adapters registered by applications.
5. **Parallels across sync/async** – The synchronous and asynchronous APIs expose
   the same typed ergonomics.

## Architecture Overview

### Schema Adapter Protocol

```python
class SchemaAdapter(Protocol[T_contra]):
    def supports(self, obj_or_type: Any) -> bool: ...
    def create_instance(self, data: Mapping[str, Any]) -> T_contra: ...
    def to_mapping(self, instance: T_contra) -> MutableMapping[str, Any]: ...
    def iter_fields(
        self, type_or_instance: type[T_contra] | T_contra
    ) -> Iterable[FieldInfo]: ...
```

* `FieldInfo` tracks name, type annotation, default value, whether the field is
  optional, whether it is Fire-Prox-reserved, and any sentinel markers (e.g.,
  server timestamps).
* Built-in adapters cover dataclasses, plain classes with `__annotations__`, and a
  dictionary fallback. Projects can register additional adapters (attrs,
  Pydantic-lite, etc.).

Adapters are registered via `SchemaAdapterRegistry`, which provides
`register(adapter)` and `resolve(schema_definition)` APIs. Resolution occurs when a
schema is bound to a collection.

### Schema Binding

`SchemaBinding[T]` stores:

* `schema_type`: the class supplied by the developer.
* `adapter`: the adapter instance responsible for conversions.
* `validate_on`: optional runtime validation modes.
* `marshallers`: references to the `MarshallerRegistry`.
* `sentinel_fields`: metadata for server timestamps and other special sentinels.
* `partial_projection_type`: lazily generated `Partial[T]` to model query
  projections.

Bindings are attached to `FireCollection[T]` and flow into derived query objects
and `FireObject[T]` instances.

### Generic Types

`FireCollection` and `FireObject` become generics so static analyzers understand
which schema applies:

```python
T_co = TypeVar("T_co", covariant=True)

class FireCollection(Generic[T_co]):
    def with_schema(self, schema: type[T_co], *, validate_on=None, marshallers=None) -> FireCollection[T_co]:
        ...

class FireObject(Generic[T_co]):
    schema_instance: T_co | None
    raw_data: MutableMapping[str, Any]
```

When no schema is bound, `T_co` defaults to `Mapping[str, Any]`. Static tools then
fall back to the current dictionary-based API.

## Query and Aggregation Typing

* `FireQuery[T_co]` mirrors the collection's type parameter.
* Projection helpers (`select`, `only`, `fields`) produce `FireQuery[Partial[T_co]]`
  where each field becomes optional and unselected fields are typed as
  `Unknown = Any` to model absence.
* Aggregate operators return typed results, e.g., `CountResult[int]` or
  `AggregationResult[TField]`, allowing linters to verify comparisons and arithmetic.
* Cursor operations (`start_after`, `start_at`) accept either schema instances or
  raw dictionaries; overloads ensure IDEs surface type hints.

## Server Timestamp Strategy

* Define `class ServerTimestamp: ...` as a lightweight sentinel type with
  `@final` annotation.
* Provide helper annotation `from fire_prox.typing import ServerTimestampField` to
  express `Annotated[datetime.datetime | None, ServerTimestampField()]`.
* The adapter serializes a `ServerTimestamp` instance to
  `firestore.SERVER_TIMESTAMP` and deserializes Firestore timestamps to
  `datetime.datetime` values while preserving the sentinel on pending writes.
* Diffing logic treats sentinel fields as dirty only when the developer explicitly
  sets them, avoiding spurious updates.

## Partial Documents and Missing Fields

* When Firestore documents lack fields present in the schema, adapters populate
  the schema instance with default values if available or the `Missing` sentinel.
* Static analyzers view these attributes as `Optional[...]` to reflect uncertainty.
* A convenience API `fire_object.ensure_defaults()` can populate missing values
  using adapter defaults without persisting changes, helping developers migrate data.

## Static Tooling Integration

1. **Type Hints** – Public methods expose precise type signatures so mypy, pyright,
   and IDEs understand return values.
2. **Stubs** – Optionally ship `.pyi` stubs for generated adapter types to improve
   IntelliSense when runtime introspection is insufficient.
3. **Linter Hooks** – Provide Ruff plugins or custom checks that flag string-based
   field names not present in the schema during query construction.
4. **Editor Enhancements** – Offer utilities that return the schema's field names
   as `Literal[...]` types to fuel auto-completion in DSL-like contexts.

## Mutation Semantics

* **Schema-first** – Developers modify `fire_object.schema_instance`. Fire-Prox
  compares serialized versions on save to detect dirty fields.
* **Dynamic fallback** – Direct attribute access continues to work. When a schema
  exists, attribute writes update both the raw dictionary and the schema instance.
* **Partial save** – `fire_object.save(fields=[...])` supports field names expressed
  as `Literal` values generated from the schema adapter, enabling static checking of
  field lists.

## Async Parity

The async API mirrors the synchronous behavior. Type aliases ensure
`AsyncFireCollection[User]` and `AsyncFireQuery[User]` present identical type
information to editors.

## Marshalling Registry

* Default handlers cover enums, timedeltas, decimal, UUID, tuples, and custom
  datatypes as needed.
* Marshallers run during `to_mapping` and `create_instance` and expose type
  information so static tools know the field's true type even if Firestore stores a
  primitive representation.

## Migration Plan

1. **Phase 0** – Implement adapter protocol, registry, and collection binding with
   dataclass support. Expose generics but keep validation disabled by default.
2. **Phase 1** – Add query typing, partial projection modeling, and server
   timestamp handling. Release stub files for `FireCollection` and `FireObject`.
3. **Phase 2** – Expand marshaller library and add optional runtime validation for
   teams ready for stricter enforcement.
4. **Phase 3** – Gather feedback, polish IDE integrations, and document best
   practices.

## Testing Strategy

* Unit tests for adapter conversions, sentinel handling, and partial projections.
* Type-checking tests using mypy/pyright to ensure generics work as expected.
* Integration tests covering synchronous and asynchronous save/fetch/query flows
  with schema-bound collections.

## Outstanding Questions

1. How aggressively should Fire-Prox generate stub files vs. relying on runtime
   annotations?
2. What is the ergonomic story for developers who want runtime validation only in
   certain environments (e.g., staging but not production)?
3. Should schema adapters support computed properties that derive from multiple
   Firestore fields, and if so, how are they typed?
4. Can we expose migration helpers that scan existing documents and suggest schema
   defaults without guaranteeing correctness?

