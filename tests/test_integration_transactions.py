"""
Integration tests for Firestore transactions (synchronous version).

Tests transaction support for atomic read-modify-write operations using
the @firestore.transactional decorator pattern.
"""

import pytest
from google.cloud import firestore

from src.fire_prox import FireProx
from src.fire_prox.testing import testing_client


@pytest.fixture
def db():
    """Create a FireProx instance connected to the emulator."""
    client = testing_client()
    return FireProx(client)


@pytest.fixture
def test_collection(db):
    """Return a test collection name."""
    return db.collection('transactions_test_collection')


class TestBasicTransactions:
    """Test basic transaction operations."""

    def test_basic_transaction_read_write(self, test_collection):
        """Test basic transaction with read and write."""
        # Create a document first
        doc = test_collection.new()
        doc.name = 'Alice'
        doc.credits = 100
        doc.save(doc_id='user1')

        # Use transaction to update
        transaction = test_collection.transaction()

        @firestore.transactional
        def update_credits(transaction):
            user = test_collection.doc('user1')
            user.fetch(transaction=transaction)
            user.credits += 50
            user.save(transaction=transaction)

        update_credits(transaction)

        # Verify the update
        user = test_collection.doc('user1')
        user.fetch(force=True)
        assert user.credits == 150

    def test_multi_document_transaction(self, test_collection):
        """Test transaction with multiple documents (transfer credits)."""
        # Create two users
        alice = test_collection.new()
        alice.name = 'Alice'
        alice.credits = 100
        alice.save(doc_id='alice')

        bob = test_collection.new()
        bob.name = 'Bob'
        bob.credits = 50
        bob.save(doc_id='bob')

        # Transfer credits using transaction
        transaction = test_collection.transaction()

        @firestore.transactional
        def transfer_credits(transaction, from_id, to_id, amount):
            from_user = test_collection.doc(from_id)
            to_user = test_collection.doc(to_id)

            # All reads must happen before writes
            from_user.fetch(transaction=transaction)
            to_user.fetch(transaction=transaction)

            # Modify locally
            from_user.credits -= amount
            to_user.credits += amount

            # Write within transaction
            from_user.save(transaction=transaction)
            to_user.save(transaction=transaction)

        transfer_credits(transaction, 'alice', 'bob', 30)

        # Verify both users were updated atomically
        alice_after = test_collection.doc('alice')
        alice_after.fetch()
        assert alice_after.credits == 70

        bob_after = test_collection.doc('bob')
        bob_after.fetch()
        assert bob_after.credits == 80

    def test_transaction_from_db(self, db, test_collection):
        """Test creating transaction from db object."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.value = 10
        doc.save(doc_id='test1')

        # Create transaction from db
        transaction = db.transaction()

        @firestore.transactional
        def update_value(transaction):
            user = test_collection.doc('test1')
            user.fetch(transaction=transaction)
            user.value += 5
            user.save(transaction=transaction)

        update_value(transaction)

        # Verify
        user = test_collection.doc('test1')
        user.fetch()
        assert user.value == 15

    def test_transaction_from_document(self, test_collection):
        """Test creating transaction from document object."""
        # Create a document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.score = 100
        doc.save(doc_id='test2')

        # Create transaction from document
        user = test_collection.doc('test2')
        transaction = user.transaction()

        @firestore.transactional
        def update_score(transaction):
            user.fetch(transaction=transaction)
            user.score += 25
            user.save(transaction=transaction)

        update_score(transaction)

        # Verify
        user.fetch(force=True)
        assert user.score == 125


class TestTransactionsWithAtomicOperations:
    """Test transactions combined with atomic operations."""

    def test_transaction_with_array_union(self, test_collection):
        """Test ArrayUnion within a transaction."""
        # Create document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.tags = ['python']
        doc.save(doc_id='user_tags')

        # Use transaction with atomic operation
        transaction = test_collection.transaction()

        @firestore.transactional
        def add_tags(transaction):
            user = test_collection.doc('user_tags')
            user.fetch(transaction=transaction)
            user.array_union('tags', ['firestore', 'database'])
            user.save(transaction=transaction)

        add_tags(transaction)

        # Verify
        user = test_collection.doc('user_tags')
        user.fetch(force=True)
        assert set(user.tags) == {'python', 'firestore', 'database'}

    def test_transaction_with_increment(self, test_collection):
        """Test Increment within a transaction."""
        # Create document
        doc = test_collection.new()
        doc.name = 'Test User'
        doc.visits = 10
        doc.save(doc_id='user_visits')

        # Use transaction with increment
        transaction = test_collection.transaction()

        @firestore.transactional
        def increment_visits(transaction):
            user = test_collection.doc('user_visits')
            user.fetch(transaction=transaction)
            user.increment('visits', 1)
            user.save(transaction=transaction)

        increment_visits(transaction)

        # Verify
        user = test_collection.doc('user_visits')
        user.fetch(force=True)
        assert user.visits == 11


class TestTransactionErrorCases:
    """Test error handling in transactions."""

    def test_transaction_on_detached_raises_error(self, test_collection):
        """Test that creating transaction from DETACHED object raises error."""
        # Create DETACHED object
        doc = test_collection.new()

        # Attempt to create transaction from DETACHED
        with pytest.raises(ValueError, match="Cannot .* on a DETACHED FireObject"):
            doc.transaction()

    def test_save_detached_in_transaction_raises_error(self, test_collection):
        """Test that saving DETACHED object in transaction raises error."""
        # Create DETACHED object
        doc = test_collection.new()
        doc.name = 'Test'

        # Attempt to save DETACHED in transaction
        transaction = test_collection.transaction()

        @firestore.transactional
        def create_doc(transaction):
            doc.save(doc_id='test_detached', transaction=transaction)

        with pytest.raises(ValueError, match="Cannot create new documents.*within a transaction"):
            create_doc(transaction)

    def test_transaction_with_field_updates(self, test_collection):
        """Test transaction with regular field updates."""
        # Create document
        doc = test_collection.new()
        doc.name = 'Alice'
        doc.status = 'pending'
        doc.credits = 100
        doc.save(doc_id='user_status')

        # Update multiple fields in transaction
        transaction = test_collection.transaction()

        @firestore.transactional
        def process_user(transaction):
            user = test_collection.doc('user_status')
            user.fetch(transaction=transaction)
            user.status = 'active'
            user.credits += 10
            user.save(transaction=transaction)

        process_user(transaction)

        # Verify all updates
        user = test_collection.doc('user_status')
        user.fetch()
        assert user.status == 'active'
        assert user.credits == 110
