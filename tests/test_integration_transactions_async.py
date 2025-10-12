"""
Integration tests for Firestore transactions (asynchronous version).

Tests transaction support for atomic read-modify-write operations using
the @firestore.async_transactional decorator pattern.
"""

import pytest
from google.cloud import firestore

from src.fire_prox import AsyncFireProx
from src.fire_prox.testing import async_testing_client


@pytest.fixture
async def db():
    """Create an AsyncFireProx instance connected to the emulator."""
    client = async_testing_client()
    return AsyncFireProx(client)


@pytest.fixture
async def test_collection(db):
    """Return a test collection name."""
    return db.collection('transactions_async_test_collection')


class TestBasicTransactionsAsync:
    """Test basic async transaction operations."""

    async def test_basic_transaction_read_write(self, test_collection):
        """Test basic transaction with read and write."""
        # Create a document first
        doc = test_collection.new()
        doc.name = 'Alice'
        doc.credits = 100
        await doc.save(doc_id='user1')

        # Use transaction to update
        transaction = test_collection.transaction()

        @firestore.async_transactional
        async def update_credits(transaction):
            user = test_collection.doc('user1')
            await user.fetch(transaction=transaction)
            user.credits += 50
            await user.save(transaction=transaction)

        await update_credits(transaction)

        # Verify the update
        user = test_collection.doc('user1')
        await user.fetch(force=True)
        assert user.credits == 150

    async def test_multi_document_transaction(self, test_collection):
        """Test transaction with multiple documents (transfer credits)."""
        # Create two users
        alice = test_collection.new()
        alice.name = 'Alice'
        alice.credits = 100
        await alice.save(doc_id='alice')

        bob = test_collection.new()
        bob.name = 'Bob'
        bob.credits = 50
        await bob.save(doc_id='bob')

        # Transfer credits using transaction
        transaction = test_collection.transaction()

        @firestore.async_transactional
        async def transfer_credits(transaction, from_id, to_id, amount):
            from_user = test_collection.doc(from_id)
            to_user = test_collection.doc(to_id)

            # All reads must happen before writes
            await from_user.fetch(transaction=transaction)
            await to_user.fetch(transaction=transaction)

            # Modify locally
            from_user.credits -= amount
            to_user.credits += amount

            # Write within transaction
            await from_user.save(transaction=transaction)
            await to_user.save(transaction=transaction)

        await transfer_credits(transaction, 'alice', 'bob', 30)

        # Verify both users were updated atomically
        alice_after = test_collection.doc('alice')
        await alice_after.fetch()
        assert alice_after.credits == 70

        bob_after = test_collection.doc('bob')
        await bob_after.fetch()
        assert bob_after.credits == 80

    async def test_transaction_from_db(self, db, test_collection):
        """Test creating transaction from db object."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.value = 10
        await doc.save(doc_id='test1')

        # Create transaction from db
        transaction = db.transaction()

        @firestore.async_transactional
        async def update_value(transaction):
            user = test_collection.doc('test1')
            await user.fetch(transaction=transaction)
            user.value += 5
            await user.save(transaction=transaction)

        await update_value(transaction)

        # Verify
        user = test_collection.doc('test1')
        await user.fetch()
        assert user.value == 15

    async def test_transaction_from_document(self, test_collection):
        """Test creating transaction from document object."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.score = 100
        await doc.save(doc_id='test2')

        # Create transaction from document
        user = test_collection.doc('test2')
        transaction = user.transaction()

        @firestore.async_transactional
        async def update_score(transaction):
            await user.fetch(transaction=transaction)
            user.score += 25
            await user.save(transaction=transaction)

        await update_score(transaction)

        # Verify
        await user.fetch(force=True)
        assert user.score == 125


class TestTransactionsWithAtomicOperationsAsync:
    """Test async transactions combined with atomic operations."""

    async def test_transaction_with_array_union(self, test_collection):
        """Test ArrayUnion within a transaction."""
        # Create document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python']
        await doc.save(doc_id='user_tags')

        # Use transaction with atomic operation
        transaction = test_collection.transaction()

        @firestore.async_transactional
        async def add_tags(transaction):
            user = test_collection.doc('user_tags')
            await user.fetch(transaction=transaction)
            user.array_union('tags', ['firestore', 'database'])
            await user.save(transaction=transaction)

        await add_tags(transaction)

        # Verify
        user = test_collection.doc('user_tags')
        await user.fetch(force=True)
        assert set(user.tags) == {'python', 'firestore', 'database'}

    async def test_transaction_with_increment(self, test_collection):
        """Test Increment within a transaction."""
        # Create document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.visits = 10
        await doc.save(doc_id='user_visits')

        # Use transaction with increment
        transaction = test_collection.transaction()

        @firestore.async_transactional
        async def increment_visits(transaction):
            user = test_collection.doc('user_visits')
            await user.fetch(transaction=transaction)
            user.increment('visits', 1)
            await user.save(transaction=transaction)

        await increment_visits(transaction)

        # Verify
        user = test_collection.doc('user_visits')
        await user.fetch(force=True)
        assert user.visits == 11


class TestTransactionErrorCasesAsync:
    """Test error handling in async transactions."""

    async def test_transaction_on_detached_raises_error(self, test_collection):
        """Test that creating transaction from DETACHED object raises error."""
        # Create DETACHED object
        doc = test_collection.new()

        # Attempt to create transaction from DETACHED
        with pytest.raises(ValueError, match="Cannot .* on a DETACHED FireObject"):
            doc.transaction()

    async def test_save_detached_in_transaction_raises_error(self, test_collection):
        """Test that saving DETACHED object in transaction raises error."""
        # Create DETACHED object
        doc = test_collection.new()
        doc.name = 'Test'

        # Attempt to save DETACHED in transaction
        transaction = test_collection.transaction()

        @firestore.async_transactional
        async def create_doc(transaction):
            await doc.save(doc_id='test_detached', transaction=transaction)

        with pytest.raises(ValueError, match="Cannot create new documents.*within a transaction"):
            await create_doc(transaction)

    async def test_transaction_with_field_updates(self, test_collection):
        """Test transaction with regular field updates."""
        # Create document
        doc = test_collection.new()
        doc.name = 'Alice'
        doc.status = 'pending'
        doc.credits = 100
        await doc.save(doc_id='user_status')

        # Update multiple fields in transaction
        transaction = test_collection.transaction()

        @firestore.async_transactional
        async def process_user(transaction):
            user = test_collection.doc('user_status')
            await user.fetch(transaction=transaction)
            user.status = 'active'
            user.credits += 10
            await user.save(transaction=transaction)

        await process_user(transaction)

        # Verify all updates
        user = test_collection.doc('user_status')
        await user.fetch()
        assert user.status == 'active'
        assert user.credits == 110
