"""
Pytest configuration and shared fixtures for FireProx tests.

This module provides common test fixtures using the real Firestore emulator
instead of mocks, enabling true integration testing.
"""

import pytest
from fire_prox.testing import testing_client, async_testing_client, firestore_test_harness  # noqa: F401
from fire_prox import FireProx, AsyncFireProx


# =========================================================================
# Synchronous Fixtures
# =========================================================================

@pytest.fixture
def client():
    """
    Provide a real Firestore client connected to the emulator.

    Returns:
        google.cloud.firestore.Client connected to emulator.
    """
    return testing_client()


@pytest.fixture
def db(client, firestore_test_harness):
    """
    Provide a FireProx instance connected to the test emulator.

    This fixture automatically cleans up the database before and after each test.

    Args:
        client: Real Firestore client fixture
        firestore_test_harness: Test harness for database cleanup

    Returns:
        FireProx instance for testing.
    """
    return FireProx(client)


@pytest.fixture
def users_collection(db):
    """
    Provide a users collection for testing.

    Returns:
        FireCollection for 'users' collection.
    """
    return db.collection('users')


# =========================================================================
# Asynchronous Fixtures
# =========================================================================

@pytest.fixture
def async_client():
    """
    Provide a real async Firestore client connected to the emulator.

    Returns:
        google.cloud.firestore.AsyncClient connected to emulator.
    """
    return async_testing_client()


@pytest.fixture
def async_db(async_client, firestore_test_harness):
    """
    Provide an AsyncFireProx instance connected to the test emulator.

    This fixture automatically cleans up the database before and after each test.

    Args:
        async_client: Real async Firestore client fixture
        firestore_test_harness: Test harness for database cleanup

    Returns:
        AsyncFireProx instance for testing.
    """
    return AsyncFireProx(async_client)


@pytest.fixture
def async_users_collection(async_db):
    """
    Provide an async users collection for testing.

    Returns:
        AsyncFireCollection for 'users' collection.
    """
    return async_db.collection('users')


# =========================================================================
# Shared Fixtures
# =========================================================================

@pytest.fixture
def sample_user_data():
    """
    Provide sample user data for testing.

    Returns:
        Dictionary with sample user fields.
    """
    return {
        'name': 'Ada Lovelace',
        'year': 1815,
        'occupation': 'Mathematician',
        'contributions': ['Analytical Engine', 'First Algorithm'],
    }
