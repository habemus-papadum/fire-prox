"""
Pytest configuration and shared fixtures for FireProx tests.

This module provides common test fixtures and configuration for the FireProx
test suite, including mock Firestore clients and common test data.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from google.cloud.firestore import Client as FirestoreClient
from google.cloud.firestore_v1.collection import CollectionReference
from google.cloud.firestore_v1.document import DocumentReference, DocumentSnapshot


@pytest.fixture
def mock_firestore_client():
    """
    Provide a mock Firestore client for testing.

    Returns:
        Mock FirestoreClient instance configured for basic operations.
    """
    client = Mock(spec=FirestoreClient)
    client.project = 'test-project'
    return client


@pytest.fixture
def mock_collection_ref():
    """
    Provide a mock CollectionReference for testing.

    Returns:
        Mock CollectionReference instance.
    """
    collection_ref = Mock(spec=CollectionReference)
    collection_ref.id = 'test_collection'
    collection_ref.path = 'test_collection'
    return collection_ref


@pytest.fixture
def mock_document_ref():
    """
    Provide a mock DocumentReference for testing.

    Returns:
        Mock DocumentReference instance configured with common attributes.
    """
    doc_ref = Mock(spec=DocumentReference)
    doc_ref.id = 'test_doc'
    doc_ref.path = 'test_collection/test_doc'
    return doc_ref


@pytest.fixture
def mock_document_snapshot():
    """
    Provide a mock DocumentSnapshot for testing.

    Returns:
        Mock DocumentSnapshot instance with sample data.
    """
    snapshot = Mock(spec=DocumentSnapshot)
    snapshot.exists = True
    snapshot.id = 'test_doc'
    snapshot.reference = Mock(spec=DocumentReference)
    snapshot.reference.id = 'test_doc'
    snapshot.reference.path = 'test_collection/test_doc'
    snapshot.to_dict.return_value = {
        'name': 'Test Document',
        'created': '2025-01-01',
        'count': 42
    }
    return snapshot


@pytest.fixture
def sample_document_data():
    """
    Provide sample document data for testing.

    Returns:
        Dictionary with sample document fields.
    """
    return {
        'name': 'Ada Lovelace',
        'year': 1815,
        'occupation': 'Mathematician',
        'contributions': ['Analytical Engine', 'First Algorithm'],
        'address': {
            'city': 'London',
            'country': 'United Kingdom'
        }
    }


# Pytest configuration
def pytest_configure(config):
    """
    Configure pytest with custom markers.
    """
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async (requires pytest-asyncio)"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as unit test"
    )


# Async mock helper for Python < 3.8 compatibility
def async_mock_return(return_value):
    """
    Create an async mock that returns a specific value.

    Args:
        return_value: The value to return when awaited.

    Returns:
        AsyncMock configured to return the specified value.
    """
    mock = AsyncMock()
    mock.return_value = return_value
    return mock
