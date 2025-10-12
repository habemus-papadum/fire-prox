"""
Integration tests for Phase 2 features (sync version).

Tests atomic operations, partial updates, and subcollections against
the Firestore emulator.
"""

import pytest
from src.fire_prox.testing import testing_client
from src.fire_prox import FireProx


@pytest.fixture
def db():
    """Create a FireProx instance connected to the emulator."""
    client = testing_client()
    yield FireProx(client)


@pytest.fixture
def test_collection(db):
    """Return a test collection name."""
    yield db.collection('phase2_test_collection')


class TestAtomicOperations:
    """Test atomic operations (ArrayUnion, ArrayRemove, Increment)."""

    def test_array_union_creates_new_array(self, test_collection):
        """Test ArrayUnion creates a new array if field doesn't exist."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.save(doc_id='user1')

        # Apply ArrayUnion to non-existent field
        doc.array_union('tags', ['python', 'firestore'])
        doc.save()

        # Verify the array was created (local simulation already updated state)
        assert 'tags' in doc.to_dict()
        assert set(doc.tags) == {'python', 'firestore'}

    def test_array_union_adds_to_existing_array(self, test_collection):
        """Test ArrayUnion adds elements to existing array."""
        # Create a document with an array
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python']
        doc.save(doc_id='user2')

        # Add more elements with ArrayUnion
        doc.array_union('tags', ['firestore', 'database'])
        doc.save()

        # Verify the elements were added (local simulation already updated state)
        assert set(doc.tags) == {'python', 'firestore', 'database'}

    def test_array_union_deduplicates(self, test_collection):
        """Test ArrayUnion automatically deduplicates values."""
        # Create a document with an array
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python', 'firestore']
        doc.save(doc_id='user3')

        # Add elements including duplicates
        doc.array_union('tags', ['firestore', 'database', 'python'])
        doc.save()

        # Verify deduplication (local simulation already updated state)
        assert set(doc.tags) == {'python', 'firestore', 'database'}

    def test_array_remove_from_array(self, test_collection):
        """Test ArrayRemove removes elements from array."""
        # Create a document with an array
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python', 'firestore', 'database', 'deprecated']
        doc.save(doc_id='user4')

        # Remove elements with ArrayRemove
        doc.array_remove('tags', ['deprecated'])
        doc.save()

        # Verify the element was removed (local simulation already updated state)
        assert set(doc.tags) == {'python', 'firestore', 'database'}

    def test_array_remove_multiple_elements(self, test_collection):
        """Test ArrayRemove can remove multiple elements."""
        # Create a document with an array
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python', 'firestore', 'database', 'old', 'deprecated']
        doc.save(doc_id='user5')

        # Remove multiple elements
        doc.array_remove('tags', ['old', 'deprecated'])
        doc.save()

        # Verify the elements were removed (local simulation already updated state)
        assert set(doc.tags) == {'python', 'firestore', 'database'}

    def test_increment_creates_field(self, test_collection):
        """Test Increment creates field if it doesn't exist (treats as 0)."""
        # Create a document without view_count
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.save(doc_id='user6')

        # Increment non-existent field
        doc.increment('view_count', 1)
        doc.save()

        # Verify the field was created with value 1 (local simulation already updated state)
        assert doc.view_count == 1

    def test_increment_existing_field(self, test_collection):
        """Test Increment increments existing numeric field."""
        # Create a document with a counter
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.view_count = 10
        doc.save(doc_id='user7')

        # Increment the counter
        doc.increment('view_count', 5)
        doc.save()

        # Verify the field was incremented (local simulation already updated state)
        assert doc.view_count == 15

    def test_increment_with_negative_value(self, test_collection):
        """Test Increment with negative value decrements the field."""
        # Create a document with a score
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.score = 100
        doc.save(doc_id='user8')

        # Decrement the score
        doc.increment('score', -25)
        doc.save()

        # Verify the field was decremented (local simulation already updated state)
        assert doc.score == 75

    def test_multiple_atomic_operations(self, test_collection):
        """Test combining multiple atomic operations in one save."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python']
        doc.view_count = 10
        doc.save(doc_id='user9')

        # Apply multiple atomic operations
        doc.array_union('tags', ['firestore'])
        doc.increment('view_count', 1)
        doc.save()

        # Verify both operations were applied (local simulation already updated state)
        assert set(doc.tags) == {'python', 'firestore'}
        assert doc.view_count == 11

    def test_atomic_ops_with_regular_updates(self, test_collection):
        """Test combining atomic operations with regular field updates."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python']
        doc.view_count = 10
        doc.status = 'active'
        doc.save(doc_id='user10')

        # Combine atomic ops with regular updates
        doc.array_union('tags', ['firestore'])
        doc.increment('view_count', 1)
        doc.status = 'updated'  # Regular field update
        doc.save()

        # Verify all changes were applied (local simulation already updated state)
        assert set(doc.tags) == {'python', 'firestore'}
        assert doc.view_count == 11
        assert doc.status == 'updated'

    def test_atomic_ops_on_deleted_object_raises_error(self, test_collection):
        """Test that atomic operations raise error on DELETED objects."""
        # Create and delete a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.save(doc_id='user11')
        doc.delete()

        # Attempt atomic operations on deleted object
        with pytest.raises(RuntimeError, match="Cannot .* on a DELETED FireObject"):
            doc.array_union('tags', ['python'])

        with pytest.raises(RuntimeError, match="Cannot .* on a DELETED FireObject"):
            doc.array_remove('tags', ['python'])

        with pytest.raises(RuntimeError, match="Cannot .* on a DELETED FireObject"):
            doc.increment('count', 1)

    def test_atomic_op_then_vanilla_modification_raises_error(self, test_collection):
        """Test that atomic op followed by vanilla modification on same field raises error."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python']
        doc.save(doc_id='mutex1')

        # Apply atomic operation
        doc.array_union('tags', ['firestore'])

        # Attempt to modify the same field directly - should raise ValueError
        with pytest.raises(ValueError, match="Cannot modify field 'tags' directly.*pending atomic operation"):
            doc.tags = ['java']

    def test_vanilla_modification_then_atomic_op_raises_error(self, test_collection):
        """Test that vanilla modification followed by atomic op on same field raises error."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.view_count = 10
        doc.save(doc_id='mutex2')

        # Modify field directly
        doc.view_count = 20

        # Attempt to use atomic operation on the same field - should raise ValueError
        with pytest.raises(ValueError, match="Cannot perform atomic increment.*field has been modified directly"):
            doc.increment('view_count', 5)

    def test_save_creates_clean_boundary_for_mutual_exclusivity(self, test_collection):
        """Test that save() clears constraints allowing different operation types."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.view_count = 10
        doc.tags = ['python']
        doc.save(doc_id='mutex3')

        # Use atomic op on one field
        doc.increment('view_count', 5)
        doc.save()

        # After save, should be able to use vanilla modification on the same field
        doc.view_count = 100
        assert doc.view_count == 100

        # Save again
        doc.save()

        # After save, should be able to use atomic op on the same field
        doc.increment('view_count', 1)
        assert doc.view_count == 101

    def test_atomic_on_one_field_vanilla_on_another_allowed(self, test_collection):
        """Test that atomic ops on one field and vanilla on another field is allowed."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.view_count = 10
        doc.tags = ['python']
        doc.save(doc_id='mutex4')

        # Atomic op on one field, vanilla on another - should work
        doc.increment('view_count', 5)
        doc.tags = ['java', 'kotlin']  # Different field - allowed
        doc.save()

        # Verify both operations succeeded
        assert doc.view_count == 15
        assert set(doc.tags) == {'java', 'kotlin'}


class TestAtomicOperationsLocalSimulation:
    """Test that atomic operations immediately update local state and persist correctly."""

    def test_array_union_local_simulation_persists(self, test_collection):
        """Test ArrayUnion immediately updates local state and persists to server."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python']
        doc.save(doc_id='sim1')

        # Apply ArrayUnion and verify immediate local update
        doc.array_union('tags', ['firestore', 'database'])
        assert set(doc.tags) == {'python', 'firestore', 'database'}  # Immediate visibility

        # Save and verify local state unchanged
        doc.save()
        assert set(doc.tags) == {'python', 'firestore', 'database'}  # Still visible after save

        # Fetch from server and verify persistence
        doc.fetch(force=True)
        assert set(doc.tags) == {'python', 'firestore', 'database'}  # Server has correct value

    def test_array_remove_local_simulation_persists(self, test_collection):
        """Test ArrayRemove immediately updates local state and persists to server."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python', 'firestore', 'database', 'deprecated']
        doc.save(doc_id='sim2')

        # Apply ArrayRemove and verify immediate local update
        doc.array_remove('tags', ['deprecated', 'database'])
        assert set(doc.tags) == {'python', 'firestore'}  # Immediate visibility

        # Save and verify local state unchanged
        doc.save()
        assert set(doc.tags) == {'python', 'firestore'}  # Still visible after save

        # Fetch from server and verify persistence
        doc.fetch(force=True)
        assert set(doc.tags) == {'python', 'firestore'}  # Server has correct value

    def test_increment_local_simulation_persists(self, test_collection):
        """Test Increment immediately updates local state and persists to server."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.view_count = 100
        doc.save(doc_id='sim3')

        # Apply Increment and verify immediate local update
        doc.increment('view_count', 42)
        assert doc.view_count == 142  # Immediate visibility

        # Save and verify local state unchanged
        doc.save()
        assert doc.view_count == 142  # Still visible after save

        # Fetch from server and verify persistence
        doc.fetch(force=True)
        assert doc.view_count == 142  # Server has correct value

    def test_multiple_atomic_operations_local_simulation_persists(self, test_collection):
        """Test multiple atomic operations all update locally and persist correctly."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python']
        doc.view_count = 10
        doc.score = 100
        doc.save(doc_id='sim4')

        # Apply multiple atomic operations and verify immediate local updates
        doc.array_union('tags', ['firestore', 'database'])
        doc.increment('view_count', 5)
        doc.increment('score', -20)

        assert set(doc.tags) == {'python', 'firestore', 'database'}  # Immediate visibility
        assert doc.view_count == 15  # Immediate visibility
        assert doc.score == 80  # Immediate visibility

        # Save and verify local state unchanged
        doc.save()
        assert set(doc.tags) == {'python', 'firestore', 'database'}  # Still visible after save
        assert doc.view_count == 15  # Still visible after save
        assert doc.score == 80  # Still visible after save

        # Fetch from server and verify persistence
        doc.fetch(force=True)
        assert set(doc.tags) == {'python', 'firestore', 'database'}  # Server has correct value
        assert doc.view_count == 15  # Server has correct value
        assert doc.score == 80  # Server has correct value


class TestPartialUpdates:
    """Test partial updates with field-level dirty tracking."""

    def test_partial_update_single_field(self, test_collection):
        """Test that modifying one field only updates that field."""
        # Create a document with multiple fields
        doc = test_collection.new()
        doc.name = 'Ada Lovelace'
        doc.year = 1815
        doc.occupation = 'Mathematician'
        doc.save(doc_id='ada')

        # Modify only one field
        doc.year = 1816
        assert doc.is_dirty()
        assert 'year' in doc.dirty_fields
        assert 'name' not in doc.dirty_fields
        assert 'occupation' not in doc.dirty_fields

        # Save and verify
        doc.save()
        assert not doc.is_dirty()

        # Fetch and verify all fields are correct
        doc.fetch(force=True)
        assert doc.name == 'Ada Lovelace'
        assert doc.year == 1816
        assert doc.occupation == 'Mathematician'

    def test_partial_update_multiple_fields(self, test_collection):
        """Test updating multiple fields tracks all of them."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Charles Babbage'
        doc.year = 1791
        doc.occupation = 'Mathematician'
        doc.save(doc_id='charles')

        # Modify multiple fields
        doc.year = 1792
        doc.occupation = 'Inventor'
        assert doc.is_dirty()
        assert 'year' in doc.dirty_fields
        assert 'occupation' in doc.dirty_fields
        assert 'name' not in doc.dirty_fields

        # Save and verify
        doc.save()
        assert not doc.is_dirty()

    def test_field_deletion_tracking(self, test_collection):
        """Test that deleting a field is tracked."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.temp_field = 'temporary'
        doc.save(doc_id='temp_user')

        # Delete a field
        del doc.temp_field
        assert doc.is_dirty()
        assert 'temp_field' in doc.deleted_fields

        # Save and verify field is removed
        doc.save()
        assert not doc.is_dirty()

        # Fetch and verify field is gone
        doc.fetch(force=True)
        data = doc.to_dict()
        assert 'temp_field' not in data
        assert doc.name == 'Test User'


class TestSubcollections:
    """Test subcollection support."""

    def test_create_subcollection(self, test_collection):
        """Test creating a subcollection under a document."""
        # Create a parent document
        user = test_collection.new()
        user.name = 'Ada Lovelace'
        user.save(doc_id='ada_sub')

        # Access subcollection
        posts = user.collection('posts')
        assert posts is not None
        assert posts.id == 'posts'

        # Create a document in the subcollection
        post = posts.new()
        post.title = 'On the Analytical Engine'
        post.year = 1843
        post.save(doc_id='post1')

        # Verify the document was created
        assert post.is_loaded()
        assert post.path == 'phase2_test_collection/ada_sub/posts/post1'

    def test_subcollection_on_detached_raises_error(self, test_collection):
        """Test that accessing subcollection on DETACHED object raises error."""
        # Create a DETACHED object
        doc = test_collection.new()

        # Attempt to access subcollection
        with pytest.raises(ValueError, match="Cannot .* on a DETACHED FireObject"):
            doc.collection('subcollection')

    def test_subcollection_on_deleted_raises_error(self, test_collection):
        """Test that accessing subcollection on DELETED object raises error."""
        # Create and delete a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.save(doc_id='deleted_user')
        doc.delete()

        # Attempt to access subcollection
        with pytest.raises(RuntimeError, match="Cannot .* on a DELETED FireObject"):
            doc.collection('subcollection')

    def test_nested_subcollections(self, test_collection):
        """Test creating nested subcollections (3+ levels)."""
        # Create parent document
        user = test_collection.new()
        user.name = 'Ada Lovelace'
        user.save(doc_id='ada_nested')

        # Create post in subcollection
        posts = user.collection('posts')
        post = posts.new()
        post.title = 'Analysis of the Analytical Engine'
        post.save(doc_id='post1')

        # Create comment in nested subcollection
        comments = post.collection('comments')
        comment = comments.new()
        comment.text = 'Brilliant work!'
        comment.author = 'Charles Babbage'
        comment.save(doc_id='comment1')

        # Verify nested path
        assert comment.path == 'phase2_test_collection/ada_nested/posts/post1/comments/comment1'
        assert comment.is_loaded()
