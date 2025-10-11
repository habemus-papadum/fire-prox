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
Places unit test files in the `src` directory near the code it is testing with a descriptive name of the form `test_*.py`

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

### Documentation
Documentation uses **numpy** formatted docstrings.  

```bash
# Serve documentation locally with live reload
uv run mkdocs serve

# Build documentation site
uv run mkdocs build
```

## Architecture

### Always make sure to support async!
The underlying native firestore api supports both sync and async operations, and fire-prox should support both modes as well.  

### Status
Currently there is a full architectural design document at `./Architectural_Blueprint.md`, but actual development has not started. 

## Implementation Roadmap

Per the architectural blueprint (`Architectural_Blueprint.md`), development follows these phases:

**Phase 1** (Foundation): Core FireObject with state machine, basic lifecycle methods (fetch, delete, simple save)

**Phase 2** (Enhancement): Efficient partial updates via dirty tracking, subcollection support, query builder, snapshot hydration

**Phase 3** (Advanced): ProxiedMap/ProxiedList for nested mutation tracking, automatic translation to Firestore atomic operations (ArrayUnion, ArrayRemove)

**Phase 4** (Polish): Firestore constraint enforcement, comprehensive documentation, error handling

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

- **FireObject** (`src/fire_prox/__init__.py`): Central proxy class with state management and dynamic attribute handling via `__getattr__`, `__setattr__`, `__delattr__`
- **FirestoreTestHarness** (`src/fire_prox/testing/__init__.py`): Test utility for clean Firestore emulator state
- **ProxiedMap/ProxiedList** (planned): Transparent mutation tracking for nested structures

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

### Firebase Emulator Configuration

Configured in `firebase.json`:
- Firestore emulator runs on port 8080
- UI enabled for debugging
- Multi-project mode enabled (`singleProjectMode: false`)

Default test project ID: `fire-prox-testing`



## Reference Implementation Pattern

When implementing FireObject methods, follow this pattern from the native API:

```python
# Native API (verbose):
doc_ref = client.collection('users').document('alovelace')
doc = doc_ref.get()
if doc.exists:
    data = doc.to_dict()
    data['year'] = 1816
    doc_ref.update(data)

# Target Fire-Prox API (intuitive):
user = db.doc('users/alovelace')  # ATTACHED state
user.year = 1816                  # Auto-fetches data, marks dirty
await user.save()                 # Partial update of only 'year' field
```

The goal is to eliminate boilerplate while maintaining compatibility with the underlying google-cloud-firestore library for complex operations.
