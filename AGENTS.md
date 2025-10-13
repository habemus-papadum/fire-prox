# AGENTS.md

This file provides guidance to AI Agents when working with code in this repository.

## Project Overview

Fire-Prox is a schemaless, state-aware proxy library for Google Cloud Firestore designed to accelerate rapid prototyping. Unlike traditional Object-Document Mappers (ODMs), Fire-Prox embraces dynamic, schema-free development by providing an intuitive, Pythonic interface that reduces boilerplate and aligns with object-oriented programming patterns.

**Key Philosophy**: Fire-Prox is an "anti-ODM" for the prototyping stage, wrapping (not replacing) the official `google-cloud-firestore` library to provide a higher-level abstraction optimized for developer velocity during rapid iteration.

## Development Commands

### Setup
The environment will likely already have been setup, but for you reference, here are the steps:

```bash
# Install Python dependencies (uses uv for fast dependency resolution)
uv sync --frozen

# Install Node.js dependencies (for Firebase emulator tools)
pnpm install
```

Add python libraries using
```bash
uv add <package>
```
(add `--dev` for dev depedencies)

### Testing
Places unit test files in the `tests` directory near with a descriptive name of the form `test_*.py`

```bash
# Run all tests (launches Firebase emulators automatically)
./test.sh
# OR
pnpm test

# Run with verbose output
./test.sh -v

# Run specific test by pattern
./test.sh -k test_specific

# Run with short traceback format
./test.sh --tb=short

# Combine multiple pytest options
./test.sh -v -k test_fire_prox

# Stop on first failure
./test.sh -x

# Run with coverage
./test.sh --cov=src
```

**Important**: The `test.sh` script automatically manages Firebase emulator lifecycle:
1. Starts local Firestore emulator (port 8080)
2. Runs pytest with any additional arguments you provide
3. Tears down emulator after tests complete

### Linting
```bash
# Run Ruff linter (configured in pyproject.toml)
uv run ruff check src/

# Auto-fix linting issues
uv run ruff check --fix src/
```

### Static Typing Fixtures
- Positive and negative fixtures live in `tests/static_typing/`.
- Run `uv run pyright tests/static_typing/post_hoc_schema_pass.py` for a quick check.
- The Pyright-based unit test `tests/test_static_typing_post_hoc_schema.py` ensures the typing metadata remains healthy.

### Documentation
Documentation uses **numpy** formatted docstrings.  

```bash
# Serve documentation locally with live reload
uv run mkdocs serve

# Build documentation site
uv run mkdocs build
```

## Architecture

### Dual API: Sync and Async

**FireProx provides both synchronous and asynchronous implementations:**

- **Synchronous API**: `FireProx`, `FireObject`, `FireCollection` - Wraps `firestore.Client`
- **Asynchronous API**: `AsyncFireProx`, `AsyncFireObject`, `AsyncFireCollection` - Wraps `firestore.AsyncClient`

**Base Class Architecture**: To maximize code reuse, FireProx uses base classes:
- `BaseFireObject`: Shared state management, properties, and validation logic
- `BaseFireCollection`: Shared collection properties and string representations
- `BaseFireProx`: Shared path validation and client access

**Development Principle**: When implementing new features, **always implement for both sync and async versions**. Use base classes for shared logic (state management, validation, properties) and implement only I/O operations separately in concrete classes.

### Key Differences: Sync vs Async

1. **Lazy Loading**:
   - **Sync** (`FireObject`): ATTACHED objects automatically fetch on attribute access
   - **Async** (`AsyncFireObject`): Requires explicit `await fetch()` (Python limitation: no async `__getattr__`)

2. **Method Signatures**:
   - Sync: `user.save()`, `user.fetch()`, `user.delete()`
   - Async: `await user.save()`, `await user.fetch()`, `await user.delete()`

### Current Status

**Phase 1: Complete ✅**
- Base class architecture implemented
- Both sync and async implementations delivered
- State machine (DETACHED, ATTACHED, LOADED, DELETED)
- Basic lifecycle methods (fetch, save, delete)
- 33 integration tests passing (16 sync + 17 async)

## Core Features

### Architecture
**State Machine**: Four-state lifecycle (DETACHED → ATTACHED → LOADED → DELETED). Enables lazy loading, dirty tracking, and safe lifecycle management. `doc.is_loaded()`, `doc.is_dirty()`.

**Dual API**: Full sync (`FireProx`, `FireObject`) and async (`AsyncFireProx`, `AsyncFireObject`) with shared base classes. `await async_user.save()` vs `user.save()`.

**Dynamic Schema**: Schemaless attribute handling. `user.name = 'Ada'; user.save()` - no models, no schemas, pure Python.

### Data Operations
**Dirty Tracking**: Field-level change detection. `user.email = 'new@x.com'; user.dirty_fields → {'email'}`. Enables partial updates (50-90% bandwidth reduction).

**Atomic Operations**: Concurrency-safe server-side operations. `doc.increment('views', 1); doc.array_union('tags', ['new'])`. No read-modify-write races.

**Subcollections**: Hierarchical data via `.collection()`. `user.collection('posts').new()` creates `users/{id}/posts/{post-id}`.

**Document References**: Auto-hydration and lazy loading. Assign `post.author = user`, read back as FireObject. Supports nested refs in lists/dicts.

**Batch Operations**: Atomic multi-document writes (up to 500). `batch = db.batch(); doc.save(batch=batch); batch.commit()`. One network round-trip.

### Querying & Analytics
**Query Builder**: Chainable interface. `users.where('age', '>', 25).order_by('score', 'DESCENDING').limit(10).get()`. Returns hydrated FireObjects.

**Pagination**: Cursor-based navigation. `page1.get(); page2 = query.start_after({'age': last_age}).get()`. Efficient large dataset traversal.

**Projections**: Field-level query optimization. `users.select('name', 'email').get()` returns dicts with only requested fields. 50-95% bandwidth savings.

**Aggregations**: Server-side analytics. `collection.count()`, `orders.sum('total')`, `users.avg('age')`. No document transfer, 2-10x faster.

### Advanced
**Transactions**: Decorator pattern for ACID operations. `@firestore.transactional def transfer(txn): ...`. Auto-retry on conflicts.

**Real-time Listeners**: Live updates via `on_snapshot()`. Sync callbacks or async handlers. `collection.on_snapshot(lambda docs: process(docs))`.

**Vector Embeddings**: `FireVector` class for semantic search. Integrates with Firestore's vector search capabilities.

**Native Integration**: `FireObject.from_snapshot(snap)` enables seamless use of native Firestore queries when needed. Best of both worlds.

## Implementation Roadmap

Per the architectural blueprint (`Architectural_Blueprint.md`), development follows these phases:

**Phase 1** (Foundation): ✅ COMPLETE
- Core FireObject with state machine, basic lifecycle methods
- Both sync and async implementations
- Integration tests with real Firestore emulator

**Phase 2** (Enhancement): 🚧 NEXT
- Efficient partial updates via field-level dirty tracking
- Subcollection support (`.collection()` on FireObject)
- Query builder (chainable `.where()`, `.order_by()`, `.limit()`)
- Atomic operations (ArrayUnion, ArrayRemove, Increment)
- **Must implement for both sync and async**

**Phase 3** (Advanced):
- ProxiedMap/ProxiedList for nested mutation tracking
- Automatic translation to Firestore atomic operations
- **Must work with both sync and async FireObject**

**Phase 4** (Polish):
- Firestore constraint enforcement
- Comprehensive documentation (both sync and async examples)
- Error handling refinements

## Development Notes

- **Python Version**: Requires Python 3.12+
- **Package Manager**: Uses `uv` for fast dependency management (replaces pip/venv workflows)
- **Type Checking**: Project includes `py.typed` marker for PEP 561 type checking support
- **Node Tooling**: Uses `pnpm` for Firebase Tools management
- **Emulator Dependency**: All tests require Firebase emulator; the test script manages this automatically

## Key Dependencies

- `google-cloud-firestore>=2.21.0`: Official Firestore client (Fire-Prox wraps this)
- `pytest>=8.4.2`: Testing framework
- `ruff>=0.14.0`: Fast Python linter/formatter
- `firebase-tools>=14.19.1`: Firestore emulator and CLI

### Core Design Principles

Fire-Prox centers around a **FireObject proxy** that maintains internal state to track its relationship with Firestore documents. This state machine enables:

- **Lazy loading**: Documents can be referenced without immediate database reads
- **Dirty tracking**: Only modified fields are sent during updates
- **Schemaless flexibility**: Fields can be added/modified dynamically without predefined schemas

### FireObject State Machine

The FireObject exists in one of four states:

1. **DETACHED**: Exists only in Python memory, no Firestore document yet (all data is "dirty")
2. **ATTACHED**: Linked to a Firestore path but data not fetched (lazy loading)
3. **LOADED**: Full in-memory representation with data fetched from Firestore
4. **DELETED**: Document deleted from Firestore, marked as defunct

State transitions occur via:
- `FireObject(path)` → ATTACHED
- `collection.new()` → DETACHED
- `.fetch()` or attribute access on ATTACHED → LOADED
- `.save()` on DETACHED → LOADED
- `.delete()` → DELETED

### Key Components

**Base Classes** (shared logic):
- **BaseFireObject** (`src/fire_prox/base_fire_object.py`): State management, properties, state inspection methods
- **BaseFireCollection** (`src/fire_prox/base_fire_collection.py`): Collection properties and string representations
- **BaseFireProx** (`src/fire_prox/base_fireprox.py`): Path validation and client access

**Synchronous API**:
- **FireObject** (`src/fire_prox/fire_object.py`): Sync document proxy with lazy loading
- **FireCollection** (`src/fire_prox/fire_collection.py`): Sync collection interface
- **FireProx** (`src/fire_prox/fireprox.py`): Main entry point wrapping `firestore.Client`

**Asynchronous API**:
- **AsyncFireObject** (`src/fire_prox/async_fire_object.py`): Async document proxy (explicit fetch required)
- **AsyncFireCollection** (`src/fire_prox/async_fire_collection.py`): Async collection interface
- **AsyncFireProx** (`src/fire_prox/async_fireprox.py`): Main entry point wrapping `firestore.AsyncClient`

**Shared Utilities**:
- **State** (`src/fire_prox/state.py`): State enum (DETACHED, ATTACHED, LOADED, DELETED)
- **FirestoreTestHarness** (`src/fire_prox/testing/__init__.py`): Test utility for clean emulator state
- **ProxiedMap/ProxiedList** (Phase 3 - planned): Transparent mutation tracking for nested structures

### Testing Strategy

**Prefer Integration Tests Over Mocking**: FireProx testing philosophy emphasizes integration tests with a real Firestore emulator rather than mocking. This provides:
- True end-to-end validation
- Confidence in actual Firestore behavior
- Detection of API changes in google-cloud-firestore
- Realistic error scenarios

**Test Coverage Requirements**:
- **Both sync and async**: Every feature must have integration tests for both `FireObject` and `AsyncFireObject`
- **Real emulator**: Use `firestore_test_harness` fixture, not mocks
- **Edge cases**: Test empty documents, nested data, special characters, state transitions
- **Error conditions**: Validate error messages and invalid state handling

**When to Use Mocking**: Reserve mocking for:
- Testing error conditions that are difficult to reproduce with emulator
- Unit testing internal helper methods
- Testing constraint validation before Firestore calls

**Current Test Suite**:
- 16 sync integration tests (`tests/test_integration_phase1.py`)
- 17 async integration tests (`tests/test_integration_async.py`)
- 180+ unit tests for components
- All tests use real Firestore emulator

### Testing Infrastructure

The project uses a custom test harness that ensures clean state:

```python
from fire_prox.testing import firestore_test_harness  # pytest fixture
from fire_prox.testing import firestore_harness       # context manager

# As pytest fixture
def test_example(firestore_test_harness):
    client = firestore.Client(project=firestore_test_harness.project_id)
    # Test with clean emulator database

# As context manager (for ad-hoc scripts)
with firestore_harness() as harness:
    client = firestore.Client(project=harness.project_id)
    # Interact with Firestore
```

The harness automatically:
- Deletes all documents before test starts (setup)
- Deletes all documents after test completes (teardown)
- Uses emulator endpoint from `FIRESTORE_EMULATOR_HOST` environment variable

**Writing Integration Tests for New Features**:
```python
# tests/test_integration_phase2.py
import pytest
from fire_prox import FireProx

class TestPhase2Feature:
    def test_sync_version(self, db, users_collection):
        """Test synchronous implementation."""
        user = users_collection.new()
        user.name = 'Ada'
        user.save()
        # Test assertions...

    @pytest.mark.asyncio
    async def test_async_version(self, async_db, async_users_collection):
        """Test asynchronous implementation."""
        user = async_users_collection.new()
        user.name = 'Ada'
        await user.save()
        # Test assertions...
```

### Firebase Emulator Configuration

Configured in `firebase.json`:
- Firestore emulator runs on port 8080
- UI enabled for debugging
- Multi-project mode enabled (`singleProjectMode: false`)

Default test project ID: `fire-prox-testing`



## Reference Implementation Patterns

When implementing features, provide both synchronous and asynchronous versions:

### Synchronous Pattern

```python
# Native API (verbose):
doc_ref = client.collection('users').document('alovelace')
doc = doc_ref.get()
if doc.exists:
    data = doc.to_dict()
    data['year'] = 1816
    doc_ref.update(data)

# FireProx Sync API (intuitive):
user = db.doc('users/alovelace')  # ATTACHED state
user.year = 1816                  # Auto-fetches data (lazy), marks dirty
user.save()                       # Update to Firestore
```

### Asynchronous Pattern

```python
# Native Async API (verbose):
doc_ref = client.collection('users').document('alovelace')
doc = await doc_ref.get()
if doc.exists:
    data = doc.to_dict()
    data['year'] = 1816
    await doc_ref.update(data)

# FireProx Async API (intuitive):
user = db.doc('users/alovelace')  # ATTACHED state
await user.fetch()                # Explicit fetch (no lazy loading in async)
user.year = 1816                  # Marks dirty
await user.save()                 # Update to Firestore
```

### Implementation Checklist for New Features

When adding a new feature:
- [ ] Implement shared logic in base class (if applicable)
- [ ] Implement sync version in `FireObject`/`FireCollection`/`FireProx`
- [ ] Implement async version in `AsyncFireObject`/`AsyncFireCollection`/`AsyncFireProx`
- [ ] Write sync integration tests in `tests/test_integration_*.py`
- [ ] Write async integration tests in `tests/test_integration_*_async.py`
- [ ] Update docstrings with examples for both sync and async usage
- [ ] Verify no regression in existing tests

The goal is to eliminate boilerplate while maintaining compatibility with the underlying google-cloud-firestore library for complex operations.
