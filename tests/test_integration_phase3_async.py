"""
Integration tests for Phase 3: Nested mutation tracking with proxies (async).

These tests verify that ProxiedMap and ProxiedList work correctly with
asynchronous Firestore operations.
"""

import pytest
from google.cloud import firestore

from fire_prox import AsyncFireProx
from fire_prox.proxied_map import ProxiedMap
from fire_prox.proxied_list import ProxiedList
from fire_prox.firestore_constraints import FirestoreConstraintError


@pytest.mark.asyncio
class TestPhase3NestedMutationTrackingAsync:
    """Test nested mutation tracking with ProxiedMap and ProxiedList (async)."""

    @pytest.fixture
    def db(self, async_client):
        """Create an AsyncFireProx instance."""
        return AsyncFireProx(async_client)

    @pytest.fixture
    def collection(self, db, firestore_test_harness):
        """Create a test collection."""
        return db.collection('phase3_async_users')

    async def test_dict_assignment_wraps_in_proxy(self, collection):
        """Test that assigning a dict creates a ProxiedMap."""
        user = collection.new()
        user.settings = {'theme': 'dark', 'notifications': True}

        # Assignment should wrap dict in ProxiedMap
        assert isinstance(user.settings, ProxiedMap)
        assert user.settings['theme'] == 'dark'

    async def test_list_assignment_wraps_in_proxy(self, collection):
        """Test that assigning a list creates a ProxiedList."""
        user = collection.new()
        user.tags = ['python', 'firestore']

        # Assignment should wrap list in ProxiedList
        assert isinstance(user.tags, ProxiedList)
        assert len(user.tags) == 2

    async def test_nested_dict_mutation_marks_dirty(self, collection):
        """Test that mutating nested dict marks parent as dirty."""
        user = collection.new()
        user.settings = {'theme': 'dark'}
        await user.save()

        # Object should not be dirty after save
        assert not user.is_dirty()

        # Mutate nested dict
        user.settings['theme'] = 'light'

        # Parent should be marked dirty
        assert user.is_dirty()
        assert 'settings' in user.dirty_fields

    async def test_nested_list_mutation_marks_dirty(self, collection):
        """Test that mutating nested list marks parent as dirty."""
        user = collection.new()
        user.tags = ['python']
        await user.save()

        # Object should not be dirty after save
        assert not user.is_dirty()

        # Mutate nested list
        user.tags.append('firestore')

        # Parent should be marked dirty
        assert user.is_dirty()
        assert 'tags' in user.dirty_fields

    async def test_nested_mutation_save_round_trip(self, collection):
        """Test that nested mutations persist correctly through save/fetch."""
        user = collection.new()
        user.name = 'Ada'
        user.settings = {'theme': 'dark', 'notifications': True}
        await user.save()

        # Mutate nested dict
        user.settings['theme'] = 'light'
        await user.save()

        # Fetch fresh copy
        user2 = collection.doc(user.id)
        await user2.fetch()

        # Nested mutation should be persisted
        assert user2.settings['theme'] == 'light'
        assert user2.settings['notifications'] is True

    async def test_deeply_nested_structures(self, collection):
        """Test mutation tracking in deeply nested structures."""
        user = collection.new()
        user.config = {
            'ui': {
                'theme': {
                    'colors': {
                        'primary': '#ff0000',
                        'secondary': '#00ff00'
                    }
                }
            }
        }
        await user.save()

        # Mutate deeply nested value
        user.config['ui']['theme']['colors']['primary'] = '#0000ff'

        # Parent should be marked dirty
        assert user.is_dirty()
        assert 'config' in user.dirty_fields

        # Save and verify
        await user.save()
        await user.fetch(force=True)
        assert user.config['ui']['theme']['colors']['primary'] == '#0000ff'

    async def test_mixed_nested_structures(self, collection):
        """Test mutation tracking with mixed dicts and lists."""
        user = collection.new()
        user.data = {
            'scores': [10, 20, 30],
            'metadata': {
                'tags': ['python', 'gcp'],
                'config': {'active': True}
            }
        }
        await user.save()

        # Mutate list within dict
        user.data['scores'].append(40)
        assert user.is_dirty()
        await user.save()

        # Mutate dict within dict
        user.data['metadata']['config']['active'] = False
        assert user.is_dirty()
        await user.save()

        # Verify all changes persisted
        await user.fetch(force=True)
        assert user.data['scores'] == [10, 20, 30, 40]
        assert user.data['metadata']['config']['active'] is False

    async def test_fetch_wraps_in_proxies(self, collection):
        """Test that fetched data is wrapped in proxies."""
        # Create document with native client
        doc_ref = collection._collection_ref.document()
        await doc_ref.set({
            'settings': {'theme': 'dark'},
            'tags': ['python', 'firestore']
        })

        # Fetch via AsyncFireObject
        user = collection.doc(doc_ref.id)
        await user.fetch()

        # Fetched data should be wrapped in proxies
        assert isinstance(user.settings, ProxiedMap)
        assert isinstance(user.tags, ProxiedList)

        # Mutations should be tracked
        user.settings['theme'] = 'light'
        assert user.is_dirty()

    async def test_to_dict_unwraps_proxies(self, collection):
        """Test that to_dict() returns plain Python types."""
        user = collection.new()
        user.settings = {'theme': 'dark'}
        user.tags = ['python']
        await user.save()

        # to_dict() should return plain dict/list, not proxies
        data = user.to_dict()
        assert isinstance(data['settings'], dict)
        assert isinstance(data['tags'], list)
        assert not isinstance(data['settings'], ProxiedMap)
        assert not isinstance(data['tags'], ProxiedList)

    async def test_invalid_field_name_rejected(self, collection):
        """Test that invalid field names are rejected."""
        user = collection.new()
        user.settings = {}

        # Invalid field name should raise error
        with pytest.raises(FirestoreConstraintError):
            user.settings['__invalid__'] = 'value'

    async def test_excessive_nesting_rejected(self, collection):
        """Test that excessive nesting depth is rejected."""
        user = collection.new()

        # Create deeply nested structure that exceeds limit
        data = {'level': {}}
        current = data['level']
        for i in range(25):  # Way more than MAX_NESTING_DEPTH
            current['level'] = {}
            current = current['level']

        # Should raise error due to depth limit
        with pytest.raises(FirestoreConstraintError):
            user.data = data

    async def test_list_of_dicts(self, collection):
        """Test mutation tracking with list of dicts."""
        user = collection.new()
        user.items = [
            {'name': 'item1', 'value': 10},
            {'name': 'item2', 'value': 20}
        ]
        await user.save()

        # Mutate dict within list
        user.items[0]['value'] = 15
        assert user.is_dirty()
        await user.save()

        # Verify
        await user.fetch(force=True)
        assert user.items[0]['value'] == 15

    async def test_append_dict_to_list(self, collection):
        """Test appending a dict to a proxied list."""
        user = collection.new()
        user.items = [{'name': 'item1'}]
        await user.save()

        # Append new dict
        user.items.append({'name': 'item2'})
        assert user.is_dirty()
        await user.save()

        # Verify
        await user.fetch(force=True)
        assert len(user.items) == 2
        assert user.items[1]['name'] == 'item2'

    async def test_dict_update_method(self, collection):
        """Test using dict.update() on ProxiedMap."""
        user = collection.new()
        user.settings = {'theme': 'dark'}
        await user.save()

        # Use update method
        user.settings.update({'theme': 'light', 'fontSize': 14})
        assert user.is_dirty()
        await user.save()

        # Verify
        await user.fetch(force=True)
        assert user.settings['theme'] == 'light'
        assert user.settings['fontSize'] == 14

    async def test_list_extend_method(self, collection):
        """Test using list.extend() on ProxiedList."""
        user = collection.new()
        user.tags = ['python']
        await user.save()

        # Use extend method
        user.tags.extend(['firestore', 'gcp'])
        assert user.is_dirty()
        await user.save()

        # Verify
        await user.fetch(force=True)
        assert user.tags == ['python', 'firestore', 'gcp']

    async def test_empty_dict_and_list(self, collection):
        """Test handling of empty dicts and lists."""
        user = collection.new()
        user.empty_dict = {}
        user.empty_list = []
        await user.save()

        # Verify they're still proxies
        assert isinstance(user.empty_dict, ProxiedMap)
        assert isinstance(user.empty_list, ProxiedList)

        # Mutate them
        user.empty_dict['key'] = 'value'
        user.empty_list.append('item')
        await user.save()

        # Verify
        await user.fetch(force=True)
        assert user.empty_dict['key'] == 'value'
        assert user.empty_list[0] == 'item'

    async def test_conservative_save_whole_field(self, collection):
        """Test that entire field is saved when nested value changes."""
        user = collection.new()
        user.config = {
            'theme': 'dark',
            'fontSize': 12,
            'nested': {'value': 'old'}
        }
        await user.save()

        # Change only nested value
        user.config['nested']['value'] = 'new'
        await user.save()

        # Fetch fresh copy - all fields should be present
        user2 = collection.doc(user.id)
        await user2.fetch()
        assert user2.config['theme'] == 'dark'
        assert user2.config['fontSize'] == 12
        assert user2.config['nested']['value'] == 'new'
