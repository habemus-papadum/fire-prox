"""
Integration tests for Async API using real Firestore emulator.

These tests verify that all async functionality works correctly with
a real Firestore instance (emulator).
"""

import pytest
from fire_prox import AsyncFireProx, State


class TestAsyncIntegration:
    """Integration tests for async API core functionality."""

    @pytest.mark.asyncio
    async def test_create_and_save_document(self, async_db, async_users_collection):
        """Test creating a new document and saving it asynchronously."""
        # Create new user
        user = async_users_collection.new()
        assert user.is_detached()
        assert user.state == State.DETACHED

        # Set attributes
        user.name = 'Ada Lovelace'
        user.year = 1815
        assert user.is_dirty()

        # Save with custom ID
        await user.save(doc_id='alovelace')
        assert user.is_loaded()
        assert user.state == State.LOADED
        assert not user.is_dirty()
        assert user.id == 'alovelace'
        assert user.path == 'users/alovelace'

    @pytest.mark.asyncio
    async def test_fetch_existing_document(self, async_db, async_users_collection, sample_user_data):
        """Test fetching an existing document asynchronously."""
        # Create document using native API
        doc_ref = async_users_collection._collection_ref.document('testuser')
        await doc_ref.set(sample_user_data)

        # Fetch using AsyncFireProx
        user = async_db.doc('users/testuser')
        assert user.is_attached()
        assert user.state == State.ATTACHED

        await user.fetch()
        assert user.is_loaded()
        assert user.state == State.LOADED
        assert user.to_dict()['name'] == 'Ada Lovelace'
        assert user.to_dict()['year'] == 1815

    @pytest.mark.asyncio
    async def test_update_document(self, async_db, async_users_collection):
        """Test updating an existing document asynchronously."""
        # Create and save
        user = async_users_collection.new()
        user.name = 'Ada'
        user.year = 1815
        await user.save(doc_id='ada')

        # Modify
        user.year = 1816
        assert user.is_dirty()

        await user.save()
        assert not user.is_dirty()

        # Verify update
        await user.fetch(force=True)
        assert user.to_dict()['year'] == 1816

    @pytest.mark.asyncio
    async def test_delete_document(self, async_db, async_users_collection):
        """Test deleting a document asynchronously."""
        # Create and save
        user = async_users_collection.new()
        user.name = 'Test User'
        await user.save(doc_id='testdelete')

        # Delete
        await user.delete()
        assert user.is_deleted()
        assert user.state == State.DELETED

        # Verify deletion
        doc_ref = async_users_collection._collection_ref.document('testdelete')
        snapshot = await doc_ref.get()
        assert not snapshot.exists

    @pytest.mark.asyncio
    async def test_state_transitions(self, async_db, async_users_collection):
        """Test state machine transitions asynchronously."""
        # DETACHED state
        user = async_users_collection.new()
        assert user.state == State.DETACHED
        assert user.is_detached()
        assert user.is_dirty()  # DETACHED is always dirty

        # DETACHED -> LOADED (via save)
        user.name = 'Test'
        await user.save()
        assert user.state == State.LOADED
        assert user.is_loaded()
        assert not user.is_dirty()

        # LOADED -> LOADED (modification + save)
        user.name = 'Updated'
        assert user.is_dirty()
        await user.save()
        assert not user.is_dirty()

        # LOADED -> DELETED
        await user.delete()
        assert user.state == State.DELETED
        assert user.is_deleted()

    @pytest.mark.asyncio
    async def test_attribute_operations(self, async_db, async_users_collection):
        """Test setting, getting, and deleting attributes asynchronously."""
        user = async_users_collection.new()

        # Set attributes
        user.name = 'Ada'
        user.year = 1815
        user.tags = ['math', 'computing']

        # Get attributes
        assert user.to_dict()['name'] == 'Ada'
        assert user.to_dict()['year'] == 1815
        assert user.to_dict()['tags'] == ['math', 'computing']

        # Save and fetch
        await user.save()
        await user.fetch(force=True)

        # Delete attribute
        del user.tags
        assert 'tags' not in user.to_dict()
        assert user.is_dirty()

        await user.save()
        await user.fetch(force=True)
        assert 'tags' not in user.to_dict()

    @pytest.mark.asyncio
    async def test_from_snapshot_hydration(self, async_db, async_users_collection, sample_user_data):
        """Test creating AsyncFireObject from snapshot."""
        # Create document using native API
        doc_ref = async_users_collection._collection_ref.document('snapshot_test')
        await doc_ref.set(sample_user_data)

        # Get snapshot
        snapshot = await doc_ref.get()

        # Hydrate to AsyncFireObject
        from fire_prox import AsyncFireObject
        user = AsyncFireObject.from_snapshot(snapshot)

        assert user.is_loaded()
        assert user.state == State.LOADED
        assert not user.is_dirty()
        assert user.id == 'snapshot_test'
        assert user.to_dict()['name'] == 'Ada Lovelace'

    @pytest.mark.asyncio
    async def test_collection_properties(self, async_db, async_users_collection):
        """Test AsyncFireCollection properties."""
        assert async_users_collection.id == 'users'
        assert async_users_collection.path == 'users'
        assert str(async_users_collection) == 'AsyncFireCollection(users)'

    @pytest.mark.asyncio
    async def test_async_fireprox_initialization(self, async_client):
        """Test AsyncFireProx initialization."""
        db = AsyncFireProx(async_client)
        assert db.native_client == async_client
        assert db.client == async_client

    @pytest.mark.asyncio
    async def test_path_validation(self, async_db):
        """Test path validation."""
        # Valid paths
        user = async_db.doc('users/test')  # Should not raise
        collection = async_db.collection('users')  # Should not raise

        # Invalid paths
        with pytest.raises(ValueError):
            async_db.doc('users')  # Odd segments for document

        with pytest.raises(ValueError):
            async_db.collection('users/test')  # Even segments for collection

        with pytest.raises(ValueError):
            async_db.doc('')  # Empty path

    @pytest.mark.asyncio
    async def test_error_handling(self, async_db, async_users_collection):
        """Test error handling for invalid operations."""
        user = async_users_collection.new()

        # Cannot fetch DETACHED
        with pytest.raises(ValueError):
            await user.fetch()

        # Cannot delete DETACHED
        with pytest.raises(ValueError):
            await user.delete()

        # Save and delete
        user.name = 'Test'
        await user.save()
        await user.delete()

        # Cannot save DELETED
        with pytest.raises(RuntimeError):
            await user.save()

        # Cannot fetch DELETED
        with pytest.raises(RuntimeError):
            await user.fetch()

        # Cannot delete DELETED
        with pytest.raises(RuntimeError):
            await user.delete()

    @pytest.mark.asyncio
    async def test_string_representations(self, async_db, async_users_collection):
        """Test __repr__ and __str__ methods."""
        user = async_users_collection.new()
        assert 'DETACHED' in repr(user)
        assert 'detached' in str(user).lower()

        user.name = 'Test'
        await user.save(doc_id='testrepr')

        assert 'LOADED' in repr(user)
        assert 'users/testrepr' in repr(user)
        assert 'users/testrepr' in str(user)

    @pytest.mark.asyncio
    async def test_auto_generated_id(self, async_users_collection):
        """Test saving with auto-generated ID."""
        user = async_users_collection.new()
        user.name = 'Auto ID User'

        await user.save()  # No doc_id specified

        assert user.id is not None
        assert len(user.id) > 0
        assert user.is_loaded()

    @pytest.mark.asyncio
    async def test_lazy_loading_on_attached(self, async_db, async_users_collection, sample_user_data):
        """Test that ATTACHED objects support lazy loading via threading."""
        # Create document
        doc_ref = async_users_collection._collection_ref.document('lazytest')
        await doc_ref.set(sample_user_data)

        # Get ATTACHED object
        user = async_db.doc('users/lazytest')
        assert user.state == State.ATTACHED

        # Accessing attribute triggers lazy loading (via thread)
        name = user.name  # This should work now!
        assert name == 'Ada Lovelace'

        # Object should now be LOADED
        assert user.state == State.LOADED
        assert user.is_loaded()

        # Subsequent accesses should be instant (no more fetching)
        year = user.year
        assert year == 1815

        # All data should be accessible
        assert user.occupation == 'Mathematician'

    @pytest.mark.asyncio
    async def test_lazy_loading_only_fetches_once(self, async_db, async_users_collection, sample_user_data):
        """Test that lazy loading only fetches once, then caches data."""
        # Create document
        doc_ref = async_users_collection._collection_ref.document('cachetest')
        await doc_ref.set(sample_user_data)

        # Get ATTACHED object
        user = async_db.doc('users/cachetest')
        assert user.state == State.ATTACHED

        # First attribute access triggers fetch
        _ = user.name
        assert user.state == State.LOADED

        # Modify document externally (should not affect cached data)
        await doc_ref.update({'name': 'Changed Name'})

        # Accessing cached attributes should return original values
        assert user.name == 'Ada Lovelace'  # Still cached value

        # Force refresh to see new data
        await user.fetch(force=True)
        assert user.name == 'Changed Name'

    @pytest.mark.asyncio
    async def test_lazy_loading_error_handling(self, async_db):
        """Test that lazy loading properly handles non-existent documents."""
        # Get reference to non-existent document
        user = async_db.doc('users/nonexistent')
        assert user.state == State.ATTACHED

        # Accessing attribute should raise NotFound
        from google.cloud.exceptions import NotFound
        with pytest.raises(NotFound):
            _ = user.name


class TestAsyncEdgeCases:
    """Edge case tests for async API."""

    @pytest.mark.asyncio
    async def test_empty_document(self, async_users_collection):
        """Test saving and fetching empty document."""
        user = async_users_collection.new()
        await user.save(doc_id='empty')

        assert user.to_dict() == {}

        # Fetch and verify
        await user.fetch(force=True)
        assert user.to_dict() == {}

    @pytest.mark.asyncio
    async def test_nested_data_structures(self, async_users_collection):
        """Test documents with nested dictionaries and lists."""
        user = async_users_collection.new()
        user.name = 'Test'
        user.address = {
            'city': 'London',
            'country': 'UK',
            'coordinates': [51.5074, -0.1278]
        }
        user.tags = ['tag1', 'tag2', 'tag3']

        await user.save()
        await user.fetch(force=True)

        data = user.to_dict()
        assert data['address']['city'] == 'London'
        assert data['address']['coordinates'] == [51.5074, -0.1278]
        assert data['tags'] == ['tag1', 'tag2', 'tag3']

    @pytest.mark.asyncio
    async def test_special_characters_in_data(self, async_users_collection):
        """Test documents with special characters."""
        user = async_users_collection.new()
        user.name = 'Test User \n\t\r'
        user.description = 'Special chars: ™ © ® € £ ¥'
        user.emoji = '🔥 🚀 ✨'

        await user.save()
        await user.fetch(force=True)

        data = user.to_dict()
        assert 'Special chars' in data['description']
        assert '🔥' in data['emoji']
