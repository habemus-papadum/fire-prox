# Agent Notes: Post-Hoc Schemas

Fire-Prox now supports optional schema metadata for collections. Attach a schema with `with_schema()` and use the helper aliases exposed from `fire_prox`:

- `DocRef[T]`: Annotates dataclass fields that should hold document references.
- `.schema_view()`: Produces a dataclass-typed view for IDE usage while preserving the FireObject wrapper for lifecycle calls.

Static typing fixtures live in `tests/static_typing/` and are enforced via `pyright`. Update the fixtures alongside any typing changes and run:

```bash
uv run pyright tests/static_typing/post_hoc_schema_pass.py
uv run pyright tests/static_typing/post_hoc_schema_fail.py
```

A dedicated unit test (`tests/test_static_typing_post_hoc_schema.py`) executes these commands inside the test suite, so keep the fixtures minimal and fast.
