"""
Integration tests for Phase 1 implementation using real Firestore emulator.

These tests verify that all Phase 1 functionality works correctly with
a real Firestore instance (emulator).
"""

import pytest

from fire_prox import FireProx, State


class TestPhase1Integration:
    """Integration tests for Phase 1 core functionality."""

    def test_create_and_save_document(self, db, users_collection):
        """Test creating a new document and saving it."""
        # Create new user
        user = users_collection.new()
        assert user.is_detached()
        assert user.state == State.DETACHED

        # Set attributes
        user.name = 'Ada Lovelace'
        user.year = 1815
        assert user.is_dirty()

        # Save with custom ID
        user.save(doc_id='alovelace')
        assert user.is_loaded()
        assert user.state == State.LOADED
        assert not user.is_dirty()
        assert user.id == 'alovelace'
        assert user.path == 'users/alovelace'

    def test_fetch_existing_document(self, db, users_collection, sample_user_data):
        """Test fetching an existing document."""
        # Create document using native API
        doc_ref = users_collection._collection_ref.document('testuser')
        doc_ref.set(sample_user_data)

        # Fetch using FireProx
        user = db.doc('users/testuser')
        assert user.is_attached()
        assert user.state == State.ATTACHED

        user.fetch()
        assert user.is_loaded()
        assert user.state == State.LOADED
        assert user.to_dict()['name'] == 'Ada Lovelace'
        assert user.to_dict()['year'] == 1815

    def test_update_document(self, db, users_collection):
        """Test updating an existing document."""
        # Create and save
        user = users_collection.new()
        user.name = 'Ada'
        user.year = 1815
        user.save(doc_id='ada')

        # Modify
        user.year = 1816
        assert user.is_dirty()

        user.save()
        assert not user.is_dirty()

        # Verify update
        user.fetch(force=True)
        assert user.to_dict()['year'] == 1816

    def test_delete_document(self, db, users_collection):
        """Test deleting a document."""
        # Create and save
        user = users_collection.new()
        user.name = 'Test User'
        user.save(doc_id='testdelete')

        # Delete
        user.delete()
        assert user.is_deleted()
        assert user.state == State.DELETED

        # Verify deletion
        doc_ref = users_collection._collection_ref.document('testdelete')
        snapshot = doc_ref.get()
        assert not snapshot.exists

    def test_state_transitions(self, db, users_collection):
        """Test state machine transitions."""
        # DETACHED state
        user = users_collection.new()
        assert user.state == State.DETACHED
        assert user.is_detached()
        assert user.is_dirty()  # DETACHED is always dirty

        # DETACHED -> LOADED (via save)
        user.name = 'Test'
        user.save()
        assert user.state == State.LOADED
        assert user.is_loaded()
        assert not user.is_dirty()

        # LOADED -> LOADED (modification + save)
        user.name = 'Updated'
        assert user.is_dirty()
        user.save()
        assert not user.is_dirty()

        # LOADED -> DELETED
        user.delete()
        assert user.state == State.DELETED
        assert user.is_deleted()

    def test_attribute_operations(self, db, users_collection):
        """Test setting, getting, and deleting attributes."""
        user = users_collection.new()

        # Set attributes
        user.name = 'Ada'
        user.year = 1815
        user.tags = ['math', 'computing']

        # Get attributes
        assert user.to_dict()['name'] == 'Ada'
        assert user.to_dict()['year'] == 1815
        assert user.to_dict()['tags'] == ['math', 'computing']

        # Save and fetch
        user.save()
        user.fetch(force=True)

        # Delete attribute
        del user.tags
        assert 'tags' not in user.to_dict()
        assert user.is_dirty()

        user.save()
        user.fetch(force=True)
        assert 'tags' not in user.to_dict()

    def test_from_snapshot_hydration(self, db, users_collection, sample_user_data):
        """Test creating FireObject from snapshot."""
        # Create document using native API
        doc_ref = users_collection._collection_ref.document('snapshot_test')
        doc_ref.set(sample_user_data)

        # Get snapshot
        snapshot = doc_ref.get()

        # Hydrate to FireObject
        from fire_prox import FireObject
        user = FireObject.from_snapshot(snapshot)

        assert user.is_loaded()
        assert user.state == State.LOADED
        assert not user.is_dirty()
        assert user.id == 'snapshot_test'
        assert user.to_dict()['name'] == 'Ada Lovelace'

    def test_collection_properties(self, db, users_collection):
        """Test FireCollection properties."""
        assert users_collection.id == 'users'
        assert users_collection.path == 'users'
        assert str(users_collection) == 'FireCollection(users)'

    def test_fireprox_initialization(self, client):
        """Test FireProx initialization."""
        db = FireProx(client)
        assert db.native_client == client
        assert db.client == client

    def test_path_validation(self, db):
        """Test path validation."""
        # Valid paths
        user = db.doc('users/test')  # Should not raise
        collection = db.collection('users')  # Should not raise

        # Invalid paths
        with pytest.raises(ValueError):
            db.doc('users')  # Odd segments for document

        with pytest.raises(ValueError):
            db.collection('users/test')  # Even segments for collection

        with pytest.raises(ValueError):
            db.doc('')  # Empty path

    def test_error_handling(self, db, users_collection):
        """Test error handling for invalid operations."""
        user = users_collection.new()

        # Cannot fetch DETACHED
        with pytest.raises(ValueError):
            user.fetch()

        # Cannot delete DETACHED
        with pytest.raises(ValueError):
            user.delete()

        # Save and delete
        user.name = 'Test'
        user.save()
        user.delete()

        # Cannot save DELETED
        with pytest.raises(RuntimeError):
            user.save()

        # Cannot fetch DELETED
        with pytest.raises(RuntimeError):
            user.fetch()

        # Cannot delete DELETED
        with pytest.raises(RuntimeError):
            user.delete()

    def test_string_representations(self, db, users_collection):
        """Test __repr__ and __str__ methods."""
        user = users_collection.new()
        assert 'DETACHED' in repr(user)
        assert 'detached' in str(user).lower()

        user.name = 'Test'
        user.save(doc_id='testrepr')

        assert 'LOADED' in repr(user)
        assert 'users/testrepr' in repr(user)
        assert 'users/testrepr' in str(user)

    def test_auto_generated_id(self, users_collection):
        """Test saving with auto-generated ID."""
        user = users_collection.new()
        user.name = 'Auto ID User'

        user.save()  # No doc_id specified

        assert user.id is not None
        assert len(user.id) > 0
        assert user.is_loaded()


class TestPhase1EdgeCases:
    """Edge case tests for Phase 1."""

    def test_empty_document(self, users_collection):
        """Test saving and fetching empty document."""
        user = users_collection.new()
        user.save(doc_id='empty')

        assert user.to_dict() == {}

        # Fetch and verify
        user.fetch(force=True)
        assert user.to_dict() == {}

    def test_nested_data_structures(self, users_collection):
        """Test documents with nested dictionaries and lists."""
        user = users_collection.new()
        user.name = 'Test'
        user.address = {
            'city': 'London',
            'country': 'UK',
            'coordinates': [51.5074, -0.1278]
        }
        user.tags = ['tag1', 'tag2', 'tag3']

        user.save()
        user.fetch(force=True)

        data = user.to_dict()
        assert data['address']['city'] == 'London'
        assert data['address']['coordinates'] == [51.5074, -0.1278]
        assert data['tags'] == ['tag1', 'tag2', 'tag3']

    def test_special_characters_in_data(self, users_collection):
        """Test documents with special characters."""
        user = users_collection.new()
        user.name = 'Test User \n\t\r'
        user.description = 'Special chars: ™ © ® € £ ¥'
        user.emoji = '🔥 🚀 ✨'

        user.save()
        user.fetch(force=True)

        data = user.to_dict()
        assert 'Special chars' in data['description']
        assert '🔥' in data['emoji']
