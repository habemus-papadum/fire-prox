# FireProx Test Suite

This directory contains comprehensive unit tests for Phase 1 of the FireProx library implementation.

## Test Organization

The test suite is organized by component:

- **`test_state.py`** - Tests for the State enum (DETACHED, ATTACHED, LOADED, DELETED)
- **`test_fire_object.py`** - Tests for the FireObject core proxy class
- **`test_fire_collection.py`** - Tests for the FireCollection class
- **`test_fireprox.py`** - Tests for the FireProx main entry point

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run specific test file
```bash
pytest tests/test_state.py
pytest tests/test_fire_object.py
pytest tests/test_fire_collection.py
pytest tests/test_fireprox.py
```

### Run with coverage
```bash
pytest tests/ --cov=fire_prox --cov-report=html
```

### Run with verbose output
```bash
pytest tests/ -v
```

### Run only unit tests (excluding integration)
```bash
pytest tests/ -m unit
```

### Run async tests
```bash
pytest tests/ -k async
```

## Test Structure

Each test file follows a consistent structure:

1. **Construction Tests** - Verify object initialization
2. **Method Tests** - Verify individual method behavior
3. **State Transition Tests** - Verify state machine transitions
4. **Integration Tests** - Verify component interactions
5. **Edge Case Tests** - Verify error handling
6. **Documentation Tests** - Verify docstrings exist

## Phase 1 Test Coverage

### State Enum
- ✅ All four states defined (DETACHED, ATTACHED, LOADED, DELETED)
- ✅ String representations (__str__, __repr__)
- ✅ Enum properties and iteration
- ✅ Documentation verification

### FireObject
- ✅ Construction in all states
- ✅ State inspection methods (is_detached, is_attached, is_loaded, is_dirty, is_deleted)
- ✅ Dynamic attribute handling (__getattr__, __setattr__, __delattr__)
- ✅ Lifecycle methods (fetch, save, delete)
- ✅ State transitions as per architectural blueprint
- ✅ Factory method (from_snapshot)
- ✅ Special methods (__repr__, __str__, to_dict)
- ✅ Lazy loading behavior
- ✅ ID and path properties

### FireCollection
- ✅ Construction and initialization
- ✅ Document creation (new() -> DETACHED)
- ✅ Document reference (doc() -> ATTACHED)
- ✅ Properties (id, path, parent)
- ✅ Query method stubs (Phase 2 features)
- ✅ Special methods (__repr__, __str__)
- ✅ Integration with FireObject

### FireProx
- ✅ Construction with native client
- ✅ Document access (doc, document methods)
- ✅ Collection access (collection method)
- ✅ Path validation
- ✅ Native client access (escape hatch)
- ✅ Batch and transaction method stubs (Phase 2+ features)
- ✅ Special methods (__repr__, __str__)
- ✅ End-to-end workflow tests

## Test Fixtures

Common fixtures are defined in `conftest.py`:

- `mock_firestore_client` - Mock Firestore client
- `mock_collection_ref` - Mock CollectionReference
- `mock_document_ref` - Mock DocumentReference
- `mock_document_snapshot` - Mock DocumentSnapshot
- `sample_document_data` - Sample test data

## Current Status

All tests are currently **stubs** - they verify that:
1. Required methods and properties exist
2. Methods have correct signatures
3. Documentation exists
4. NotImplementedError is raised for unimplemented features

As Phase 1 is implemented, these stub tests should be updated to:
1. Remove the `assert True  # Placeholder for stub` lines
2. Uncomment the actual test assertions
3. Verify real behavior against specifications

## Dependencies

Required test dependencies:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Enhanced mocking

Install with:
```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

## Notes for Implementation

When implementing the actual functionality:

1. Start by uncommenting test assertions one by one
2. Run tests frequently to verify behavior
3. Ensure all state transitions match the architectural blueprint
4. Pay special attention to:
   - Dirty flag management
   - State transitions
   - DocumentReference lifecycle
   - Lazy loading triggers
   - Error handling (ValueError, RuntimeError, AttributeError)

## Future Phases

Phase 2 tests will add:
- Partial update logic (_dirty_fields set)
- Subcollection support
- Query builder functionality
- from_snapshot hydration with references

Phase 3 tests will add:
- ProxiedMap and ProxiedList
- Nested mutation tracking
- ArrayUnion/ArrayRemove optimization
- Recursive proxying
