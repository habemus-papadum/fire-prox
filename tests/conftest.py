"""
Pytest configuration and shared fixtures for FireProx tests.

This module provides common test fixtures using the real Firestore emulator
instead of mocks, enabling true integration testing.
"""

import pytest
from fire_prox.testing import testing_client, firestore_test_harness  # noqa: F401
from fire_prox import FireProx


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
