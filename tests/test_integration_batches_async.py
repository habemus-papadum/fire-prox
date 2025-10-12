"""
Integration tests for Firestore batch operations (asynchronous version).

Tests batch support for atomic multi-document write operations using
the async/await pattern.
"""

import pytest
from google.cloud import firestore
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
    return db.collection('batches_async_test_collection')


class TestBasicBatchOperationsAsync:
    """Test basic async batch set, update, and delete operations."""

    async def test_batch_set_single_document(self, test_collection):
        """Test setting a single document in a batch."""
        # Create document first
        doc = test_collection.new()
        doc.name = 'Alice'
        doc.age = 30
        await doc.save(doc_id='user1')

        # Use batch to update
        batch = test_collection.batch()

        user = test_collection.doc('user1')
        await user.fetch()
        user.age = 31
        await user.save(batch=batch)

        await batch.commit()

        # Verify the update
        user_after = test_collection.doc('user1')
        await user_after.fetch()
        assert user_after.age == 31

    async def test_batch_update_single_document(self, test_collection):
        """Test updating a single document in a batch."""
        # Create document
        doc = test_collection.new()
        doc.name = 'Bob'
        doc.score = 100
        await doc.save(doc_id='user2')

        # Use batch to update
        batch = test_collection.batch()

        user = test_collection.doc('user2')
        await user.fetch()
        user.score += 50
        await user.save(batch=batch)

        await batch.commit()

        # Verify
        user_after = test_collection.doc('user2')
        await user_after.fetch()
        assert user_after.score == 150

    async def test_batch_delete_single_document(self, test_collection):
        """Test deleting a single document in a batch."""
        # Create document
        doc = test_collection.new()
        doc.name = 'Charlie'
        await doc.save(doc_id='user3')

        # Use batch to delete
        batch = test_collection.batch()

        user = test_collection.doc('user3')
        await user.delete(batch=batch)

        await batch.commit()

        # Verify document was deleted
        user_after = test_collection.doc('user3')
        try:
            await user_after.fetch()
            assert False, "Document should not exist"
        except Exception:
            # Document doesn't exist - this is expected
            pass

    async def test_batch_multiple_sets(self, test_collection):
        """Test setting multiple documents in one batch."""
        # Create documents first
        for i in range(3):
            doc = test_collection.new()
            doc.name = f'User{i}'
            doc.value = i * 10
            await doc.save(doc_id=f'multi_set_{i}')

        # Update all in batch
        batch = test_collection.batch()

        for i in range(3):
            user = test_collection.doc(f'multi_set_{i}')
            await user.fetch()
            user.value += 100
            await user.save(batch=batch)

        await batch.commit()

        # Verify all were updated
        for i in range(3):
            user = test_collection.doc(f'multi_set_{i}')
            await user.fetch()
            assert user.value == (i * 10) + 100

    async def test_batch_multiple_deletes(self, test_collection):
        """Test deleting multiple documents in one batch."""
        # Create documents
        for i in range(3):
            doc = test_collection.new()
            doc.name = f'ToDelete{i}'
            await doc.save(doc_id=f'multi_delete_{i}')

        # Delete all in batch
        batch = test_collection.batch()

        for i in range(3):
            user = test_collection.doc(f'multi_delete_{i}')
            await user.delete(batch=batch)

        await batch.commit()

        # Verify all were deleted
        for i in range(3):
            user = test_collection.doc(f'multi_delete_{i}')
            try:
                await user.fetch()
                assert False, f"Document multi_delete_{i} should not exist"
            except Exception:
                # Document doesn't exist - this is expected
                pass


class TestMixedBatchOperationsAsync:
    """Test async batch operations with mixed set, update, and delete."""

    async def test_batch_mixed_operations(self, test_collection):
        """Test batch with set, update, and delete operations."""
        # Create initial documents
        doc1 = test_collection.new()
        doc1.name = 'ToUpdate'
        doc1.value = 10
        await doc1.save(doc_id='mixed_1')

        doc2 = test_collection.new()
        doc2.name = 'ToDelete'
        await doc2.save(doc_id='mixed_2')

        doc3 = test_collection.new()
        doc3.name = 'ToSet'
        doc3.value = 20
        await doc3.save(doc_id='mixed_3')

        # Perform mixed operations in batch
        batch = test_collection.batch()

        # Update doc1
        user1 = test_collection.doc('mixed_1')
        await user1.fetch()
        user1.value = 15
        await user1.save(batch=batch)

        # Delete doc2
        user2 = test_collection.doc('mixed_2')
        await user2.delete(batch=batch)

        # Set doc3
        user3 = test_collection.doc('mixed_3')
        await user3.fetch()
        user3.value = 30
        await user3.save(batch=batch)

        await batch.commit()

        # Verify all operations
        user1_after = test_collection.doc('mixed_1')
        await user1_after.fetch()
        assert user1_after.value == 15

        user2_after = test_collection.doc('mixed_2')
        try:
            await user2_after.fetch()
            assert False, "Document mixed_2 should not exist"
        except Exception:
            # Document doesn't exist - this is expected
            pass

        user3_after = test_collection.doc('mixed_3')
        await user3_after.fetch()
        assert user3_after.value == 30

    async def test_batch_multiple_updates_same_document(self, test_collection):
        """Test multiple updates to the same document in batch (last wins)."""
        # Create document
        doc = test_collection.new()
        doc.name = 'Test'
        doc.counter = 0
        await doc.save(doc_id='same_doc')

        # Multiple updates in batch
        batch = test_collection.batch()

        user = test_collection.doc('same_doc')
        await user.fetch()
        user.counter = 1
        await user.save(batch=batch)

        user.counter = 2
        await user.save(batch=batch)

        user.counter = 3
        await user.save(batch=batch)

        await batch.commit()

        # Verify last update wins
        user_after = test_collection.doc('same_doc')
        await user_after.fetch()
        assert user_after.counter == 3


class TestBatchWithAtomicOperationsAsync:
    """Test async batches combined with atomic operations."""

    async def test_batch_with_array_union(self, test_collection):
        """Test ArrayUnion within a batch."""
        # Create document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python']
        await doc.save(doc_id='batch_array_union')

        # Use batch with atomic operation
        batch = test_collection.batch()

        user = test_collection.doc('batch_array_union')
        await user.fetch()
        user.array_union('tags', ['firestore', 'database'])
        await user.save(batch=batch)

        await batch.commit()

        # Verify
        user_after = test_collection.doc('batch_array_union')
        await user_after.fetch()
        assert set(user_after.tags) == {'python', 'firestore', 'database'}

    async def test_batch_with_array_remove(self, test_collection):
        """Test ArrayRemove within a batch."""
        # Create document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python', 'java', 'rust']
        await doc.save(doc_id='batch_array_remove')

        # Use batch with atomic operation
        batch = test_collection.batch()

        user = test_collection.doc('batch_array_remove')
        await user.fetch()
        user.array_remove('tags', ['java'])
        await user.save(batch=batch)

        await batch.commit()

        # Verify
        user_after = test_collection.doc('batch_array_remove')
        await user_after.fetch()
        assert set(user_after.tags) == {'python', 'rust'}

    async def test_batch_with_increment(self, test_collection):
        """Test Increment within a batch."""
        # Create document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.visits = 10
        await doc.save(doc_id='batch_increment')

        # Use batch with increment
        batch = test_collection.batch()

        user = test_collection.doc('batch_increment')
        await user.fetch()
        user.increment('visits', 5)
        await user.save(batch=batch)

        await batch.commit()

        # Verify
        user_after = test_collection.doc('batch_increment')
        await user_after.fetch()
        assert user_after.visits == 15

    async def test_batch_with_multiple_atomic_operations(self, test_collection):
        """Test multiple atomic operations on different docs in batch."""
        # Create documents
        doc1 = test_collection.new()
        doc1.name = 'User1'
        doc1.tags = ['python']
        await doc1.save(doc_id='atomic_1')

        doc2 = test_collection.new()
        doc2.name = 'User2'
        doc2.score = 100
        await doc2.save(doc_id='atomic_2')

        # Use batch with multiple atomic ops
        batch = test_collection.batch()

        user1 = test_collection.doc('atomic_1')
        await user1.fetch()
        user1.array_union('tags', ['firestore'])
        await user1.save(batch=batch)

        user2 = test_collection.doc('atomic_2')
        await user2.fetch()
        user2.increment('score', 50)
        await user2.save(batch=batch)

        await batch.commit()

        # Verify both
        user1_after = test_collection.doc('atomic_1')
        await user1_after.fetch()
        assert set(user1_after.tags) == {'python', 'firestore'}

        user2_after = test_collection.doc('atomic_2')
        await user2_after.fetch()
        assert user2_after.score == 150


class TestBatchCreationAsync:
    """Test creating batches from different objects."""

    async def test_batch_from_db(self, db, test_collection):
        """Test creating batch from db object."""
        # Create document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.value = 10
        await doc.save(doc_id='batch_from_db')

        # Create batch from db
        batch = db.batch()

        user = test_collection.doc('batch_from_db')
        await user.fetch()
        user.value = 20
        await user.save(batch=batch)

        await batch.commit()

        # Verify
        user_after = test_collection.doc('batch_from_db')
        await user_after.fetch()
        assert user_after.value == 20

    async def test_batch_from_collection(self, test_collection):
        """Test creating batch from collection object."""
        # Create document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.score = 100
        await doc.save(doc_id='batch_from_collection')

        # Create batch from collection
        batch = test_collection.batch()

        user = test_collection.doc('batch_from_collection')
        await user.fetch()
        user.score = 150
        await user.save(batch=batch)

        await batch.commit()

        # Verify
        user_after = test_collection.doc('batch_from_collection')
        await user_after.fetch()
        assert user_after.score == 150

    async def test_batch_from_document(self, test_collection):
        """Test creating batch from document object."""
        # Create document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.points = 50
        await doc.save(doc_id='batch_from_document')

        # Create batch from document
        user = test_collection.doc('batch_from_document')
        batch = user.batch()

        await user.fetch()
        user.points = 75
        await user.save(batch=batch)

        await batch.commit()

        # Verify
        await user.fetch(force=True)
        assert user.points == 75


class TestBatchErrorCasesAsync:
    """Test error handling in async batches."""

    async def test_batch_with_detached_document_raises_error(self, test_collection):
        """Test that saving DETACHED object in batch raises error."""
        # Create DETACHED object
        doc = test_collection.new()
        doc.name = 'Test'

        # Attempt to save DETACHED in batch
        batch = test_collection.batch()

        with pytest.raises(ValueError, match="Cannot create new documents.*within a batch"):
            await doc.save(doc_id='test_detached', batch=batch)

    async def test_batch_on_detached_raises_error(self, test_collection):
        """Test that creating batch from DETACHED object raises error."""
        # Create DETACHED object
        doc = test_collection.new()

        # Attempt to create batch from DETACHED
        with pytest.raises(ValueError, match="Cannot .* on a DETACHED FireObject"):
            doc.batch()

    async def test_batch_delete_on_deleted_raises_error(self, test_collection):
        """Test that deleting already DELETED object in batch raises error."""
        # Create and delete document
        doc = test_collection.new()
        doc.name = 'Test'
        await doc.save(doc_id='to_delete_twice')

        user = test_collection.doc('to_delete_twice')
        await user.delete()

        # Attempt to delete again in batch
        batch = test_collection.batch()

        with pytest.raises(RuntimeError, match="Cannot delete.*on a DELETED"):
            await user.delete(batch=batch)


class TestBulkBatchOperationsAsync:
    """Test async batch operations with large numbers of documents."""

    async def test_batch_bulk_create_and_update(self, test_collection):
        """Test creating many documents then updating them in batch."""
        # Create 50 documents
        for i in range(50):
            doc = test_collection.new()
            doc.name = f'BulkUser{i}'
            doc.value = i
            await doc.save(doc_id=f'bulk_{i}')

        # Update all in batch
        batch = test_collection.batch()

        for i in range(50):
            user = test_collection.doc(f'bulk_{i}')
            await user.fetch()
            user.value = i * 2
            await user.save(batch=batch)

        await batch.commit()

        # Verify sample of updates
        for i in [0, 10, 25, 49]:
            user = test_collection.doc(f'bulk_{i}')
            await user.fetch()
            assert user.value == i * 2

    async def test_batch_bulk_delete(self, test_collection):
        """Test deleting many documents in batch."""
        # Create 50 documents
        for i in range(50):
            doc = test_collection.new()
            doc.name = f'ToDeleteBulk{i}'
            await doc.save(doc_id=f'bulk_delete_{i}')

        # Delete all in batch
        batch = test_collection.batch()

        for i in range(50):
            user = test_collection.doc(f'bulk_delete_{i}')
            await user.delete(batch=batch)

        await batch.commit()

        # Verify sample of deletes
        for i in [0, 25, 49]:
            user = test_collection.doc(f'bulk_delete_{i}')
            try:
                await user.fetch()
                assert False, f"Document bulk_delete_{i} should not exist"
            except Exception:
                # Document doesn't exist - this is expected
                pass

    async def test_batch_with_field_deletes(self, test_collection):
        """Test batch with field deletions."""
        # Create document with multiple fields
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.email = 'test@example.com'
        doc.phone = '555-1234'
        doc.address = '123 Main St'
        await doc.save(doc_id='field_delete_test')

        # Delete some fields in batch
        batch = test_collection.batch()

        user = test_collection.doc('field_delete_test')
        await user.fetch()
        del user.phone
        del user.address
        await user.save(batch=batch)

        await batch.commit()

        # Verify fields were deleted
        user_after = test_collection.doc('field_delete_test')
        await user_after.fetch()
        assert user_after.name == 'Test User'
        assert user_after.email == 'test@example.com'
        assert not hasattr(user_after, 'phone')
        assert not hasattr(user_after, 'address')


class TestBatchAtomicityAsync:
    """Test that async batch operations are atomic (all-or-nothing)."""

    async def test_batch_commit_succeeds_for_all_operations(self, test_collection):
        """Test that batch commit applies all operations atomically."""
        # Create documents
        for i in range(5):
            doc = test_collection.new()
            doc.name = f'User{i}'
            doc.counter = 0
            await doc.save(doc_id=f'atomic_test_{i}')

        # Perform batch operations
        batch = test_collection.batch()

        for i in range(5):
            user = test_collection.doc(f'atomic_test_{i}')
            await user.fetch()
            user.counter = i + 1
            await user.save(batch=batch)

        await batch.commit()

        # Verify all operations succeeded
        for i in range(5):
            user = test_collection.doc(f'atomic_test_{i}')
            await user.fetch()
            assert user.counter == i + 1
