"""
Integration tests for Phase 2 features (async version).

Tests atomic operations, partial updates, and subcollections against
the Firestore emulator using async/await.
"""

import pytest
from src.fire_prox.testing import async_testing_client
from src.fire_prox import AsyncFireProx


@pytest.fixture
async def db():
    """Create an AsyncFireProx instance connected to the emulator."""
    client = async_testing_client()
    return AsyncFireProx(client)


@pytest.fixture
async def test_collection(db):
    """Return a test collection name."""
    return db.collection('phase2_async_test_collection')


class TestAtomicOperationsAsync:
    """Test async atomic operations (ArrayUnion, ArrayRemove, Increment)."""

    async def test_array_union_creates_new_array(self, test_collection):
        """Test ArrayUnion creates a new array if field doesn't exist."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        await doc.save(doc_id='user1')

        # Apply ArrayUnion to non-existent field
        doc.array_union('tags', ['python', 'firestore'])
        await doc.save()

        # Verify the array was created
        await doc.fetch(force=True)
        assert 'tags' in doc.to_dict()
        assert set(doc.tags) == {'python', 'firestore'}

    async def test_array_union_adds_to_existing_array(self, test_collection):
        """Test ArrayUnion adds elements to existing array."""
        # Create a document with an array
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python']
        await doc.save(doc_id='user2')

        # Add more elements with ArrayUnion
        doc.array_union('tags', ['firestore', 'database'])
        await doc.save()

        # Verify the elements were added
        await doc.fetch(force=True)
        assert set(doc.tags) == {'python', 'firestore', 'database'}

    async def test_array_union_deduplicates(self, test_collection):
        """Test ArrayUnion automatically deduplicates values."""
        # Create a document with an array
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python', 'firestore']
        await doc.save(doc_id='user3')

        # Add elements including duplicates
        doc.array_union('tags', ['firestore', 'database', 'python'])
        await doc.save()

        # Verify deduplication
        await doc.fetch(force=True)
        assert set(doc.tags) == {'python', 'firestore', 'database'}

    async def test_array_remove_from_array(self, test_collection):
        """Test ArrayRemove removes elements from array."""
        # Create a document with an array
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python', 'firestore', 'database', 'deprecated']
        await doc.save(doc_id='user4')

        # Remove elements with ArrayRemove
        doc.array_remove('tags', ['deprecated'])
        await doc.save()

        # Verify the element was removed
        await doc.fetch(force=True)
        assert set(doc.tags) == {'python', 'firestore', 'database'}

    async def test_array_remove_multiple_elements(self, test_collection):
        """Test ArrayRemove can remove multiple elements."""
        # Create a document with an array
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python', 'firestore', 'database', 'old', 'deprecated']
        await doc.save(doc_id='user5')

        # Remove multiple elements
        doc.array_remove('tags', ['old', 'deprecated'])
        await doc.save()

        # Verify the elements were removed
        await doc.fetch(force=True)
        assert set(doc.tags) == {'python', 'firestore', 'database'}

    async def test_increment_creates_field(self, test_collection):
        """Test Increment creates field if it doesn't exist (treats as 0)."""
        # Create a document without view_count
        doc = test_collection.new()
        doc.name = 'Test User'
        await doc.save(doc_id='user6')

        # Increment non-existent field
        doc.increment('view_count', 1)
        await doc.save()

        # Verify the field was created with value 1
        await doc.fetch(force=True)
        assert doc.view_count == 1

    async def test_increment_existing_field(self, test_collection):
        """Test Increment increments existing numeric field."""
        # Create a document with a counter
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.view_count = 10
        await doc.save(doc_id='user7')

        # Increment the counter
        doc.increment('view_count', 5)
        await doc.save()

        # Verify the field was incremented
        await doc.fetch(force=True)
        assert doc.view_count == 15

    async def test_increment_with_negative_value(self, test_collection):
        """Test Increment with negative value decrements the field."""
        # Create a document with a score
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.score = 100
        await doc.save(doc_id='user8')

        # Decrement the score
        doc.increment('score', -25)
        await doc.save()

        # Verify the field was decremented
        await doc.fetch(force=True)
        assert doc.score == 75

    async def test_multiple_atomic_operations(self, test_collection):
        """Test combining multiple atomic operations in one save."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python']
        doc.view_count = 10
        await doc.save(doc_id='user9')

        # Apply multiple atomic operations
        doc.array_union('tags', ['firestore'])
        doc.increment('view_count', 1)
        await doc.save()

        # Verify both operations were applied
        await doc.fetch(force=True)
        assert set(doc.tags) == {'python', 'firestore'}
        assert doc.view_count == 11

    async def test_atomic_ops_with_regular_updates(self, test_collection):
        """Test combining atomic operations with regular field updates."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python']
        doc.view_count = 10
        doc.status = 'active'
        await doc.save(doc_id='user10')

        # Combine atomic ops with regular updates
        doc.array_union('tags', ['firestore'])
        doc.increment('view_count', 1)
        doc.status = 'updated'  # Regular field update
        await doc.save()

        # Verify all changes were applied
        await doc.fetch(force=True)
        assert set(doc.tags) == {'python', 'firestore'}
        assert doc.view_count == 11
        assert doc.status == 'updated'

    async def test_atomic_ops_on_deleted_object_raises_error(self, test_collection):
        """Test that atomic operations raise error on DELETED objects."""
        # Create and delete a document
        doc = test_collection.new()
        doc.name = 'Test User'
        await doc.save(doc_id='user11')
        await doc.delete()

        # Attempt atomic operations on deleted object
        with pytest.raises(RuntimeError, match="Cannot .* on a DELETED FireObject"):
            doc.array_union('tags', ['python'])

        with pytest.raises(RuntimeError, match="Cannot .* on a DELETED FireObject"):
            doc.array_remove('tags', ['python'])

        with pytest.raises(RuntimeError, match="Cannot .* on a DELETED FireObject"):
            doc.increment('count', 1)


class TestPartialUpdatesAsync:
    """Test async partial updates with field-level dirty tracking."""

    async def test_partial_update_single_field(self, test_collection):
        """Test that modifying one field only updates that field."""
        # Create a document with multiple fields
        doc = test_collection.new()
        doc.name = 'Ada Lovelace'
        doc.year = 1815
        doc.occupation = 'Mathematician'
        await doc.save(doc_id='ada')

        # Modify only one field
        doc.year = 1816
        assert doc.is_dirty()
        assert 'year' in doc.dirty_fields
        assert 'name' not in doc.dirty_fields
        assert 'occupation' not in doc.dirty_fields

        # Save and verify
        await doc.save()
        assert not doc.is_dirty()

        # Fetch and verify all fields are correct
        await doc.fetch(force=True)
        assert doc.name == 'Ada Lovelace'
        assert doc.year == 1816
        assert doc.occupation == 'Mathematician'

    async def test_partial_update_multiple_fields(self, test_collection):
        """Test updating multiple fields tracks all of them."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Charles Babbage'
        doc.year = 1791
        doc.occupation = 'Mathematician'
        await doc.save(doc_id='charles')

        # Modify multiple fields
        doc.year = 1792
        doc.occupation = 'Inventor'
        assert doc.is_dirty()
        assert 'year' in doc.dirty_fields
        assert 'occupation' in doc.dirty_fields
        assert 'name' not in doc.dirty_fields

        # Save and verify
        await doc.save()
        assert not doc.is_dirty()

    async def test_field_deletion_tracking(self, test_collection):
        """Test that deleting a field is tracked."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.temp_field = 'temporary'
        await doc.save(doc_id='temp_user')

        # Delete a field
        del doc.temp_field
        assert doc.is_dirty()
        assert 'temp_field' in doc.deleted_fields

        # Save and verify field is removed
        await doc.save()
        assert not doc.is_dirty()

        # Fetch and verify field is gone
        await doc.fetch(force=True)
        data = doc.to_dict()
        assert 'temp_field' not in data
        assert doc.name == 'Test User'


class TestSubcollectionsAsync:
    """Test async subcollection support."""

    async def test_create_subcollection(self, test_collection):
        """Test creating a subcollection under a document."""
        # Create a parent document
        user = test_collection.new()
        user.name = 'Ada Lovelace'
        await user.save(doc_id='ada_sub')

        # Access subcollection
        posts = user.collection('posts')
        assert posts is not None
        assert posts.id == 'posts'

        # Create a document in the subcollection
        post = posts.new()
        post.title = 'On the Analytical Engine'
        post.year = 1843
        await post.save(doc_id='post1')

        # Verify the document was created
        assert post.is_loaded()
        assert post.path == 'phase2_async_test_collection/ada_sub/posts/post1'

    async def test_subcollection_on_detached_raises_error(self, test_collection):
        """Test that accessing subcollection on DETACHED object raises error."""
        # Create a DETACHED object
        doc = test_collection.new()

        # Attempt to access subcollection
        with pytest.raises(ValueError, match="Cannot .* on a DETACHED FireObject"):
            doc.collection('subcollection')

    async def test_subcollection_on_deleted_raises_error(self, test_collection):
        """Test that accessing subcollection on DELETED object raises error."""
        # Create and delete a document
        doc = test_collection.new()
        doc.name = 'Test User'
        await doc.save(doc_id='deleted_user')
        await doc.delete()

        # Attempt to access subcollection
        with pytest.raises(RuntimeError, match="Cannot .* on a DELETED FireObject"):
            doc.collection('subcollection')

    async def test_nested_subcollections(self, test_collection):
        """Test creating nested subcollections (3+ levels)."""
        # Create parent document
        user = test_collection.new()
        user.name = 'Ada Lovelace'
        await user.save(doc_id='ada_nested')

        # Create post in subcollection
        posts = user.collection('posts')
        post = posts.new()
        post.title = 'Analysis of the Analytical Engine'
        await post.save(doc_id='post1')

        # Create comment in nested subcollection
        comments = post.collection('comments')
        comment = comments.new()
        comment.text = 'Brilliant work!'
        comment.author = 'Charles Babbage'
        await comment.save(doc_id='comment1')

        # Verify nested path
        assert comment.path == 'phase2_async_test_collection/ada_nested/posts/post1/comments/comment1'
        assert comment.is_loaded()
