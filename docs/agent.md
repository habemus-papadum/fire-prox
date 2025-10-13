# Fire-Prox Agent Notes

## Post-hoc Schemas

* Collections can be bound to standard library dataclasses by passing the
  schema directly to `collection("name", MyDataclass)`. The returned collection
  exposes typed `FireObject[MyDataclass]` documents while retaining the normal
  lifecycle API. Existing `with_schema()` calls remain available when you need
  to retrofit an already-referenced collection.
* FireObject instances keep schema metadata regardless of load state. The
  runtime remains permissive; schema information is advisory for static analysis
  and editor completions.
* Both synchronous and asynchronous collections and documents support schema
  binding. Queries derived from a typed collection preserve the same generic
  parameter.

## Static Typing Tests

* Static fixtures live under `tests/static_typing/`:
  * `positive.py` must pass Pyright in strict mode.
  * `negative.py` is expected to fail, confirming that incorrect assignments are
    surfaced.
* Run the automated check with `pytest tests/test_static_typing.py` or call
  `uv run pyright --project pyrightconfig.json` directly for the positive
  fixture.
