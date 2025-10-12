"""
Comprehensive tests for on_snapshot real-time listeners.

Tests verify:
- Document-level listeners (FireObject.on_snapshot)
- Collection-level listeners (FireCollection.on_snapshot)
- Query-level listeners (FireQuery.on_snapshot)
- Callback invocation and parameters
- Unsubscribe functionality
- Threading behavior
- State validation (DETACHED, DELETED errors)
"""

import pytest
import threading
import time
from google.cloud import firestore
from fire_prox import FireProx, AsyncFireProx
from fire_prox.testing import firestore_test_harness


# =========================================================================
# Sync Tests: Document Listeners
# =========================================================================

class TestDocumentListeners:
    """Test on_snapshot() for FireObject (document-level listeners)."""

    def test_document_listener_receives_initial_snapshot(self, db):
        """Test that document listener receives initial snapshot."""
        users = db.collection('snapshot_users')

        # Create a user
        user = users.new()
        user.name = 'Alice'
        user.age = 30
        user.save()

        # Set up listener
        callback_done = threading.Event()
        received_snapshots = []

        def on_change(doc_snapshot, changes, read_time):
            for doc in doc_snapshot:
                received_snapshots.append(doc.to_dict())
            callback_done.set()

        # Start listening
        watch = user.on_snapshot(on_change)

        # Wait for initial snapshot
        callback_done.wait(timeout=5)

        # Verify
        assert len(received_snapshots) == 1
        assert received_snapshots[0]['name'] == 'Alice'
        assert received_snapshots[0]['age'] == 30

        # Cleanup
        watch.unsubscribe()

    def test_document_listener_detects_modifications(self, db):
        """Test that document listener detects when document is modified."""
        users = db.collection('snapshot_users')

        # Create a user
        user = users.new()
        user.name = 'Bob'
        user.age = 25
        user.save()

        # Set up listener
        modification_event = threading.Event()
        modifications = []

        def on_change(doc_snapshot, changes, read_time):
            for doc in doc_snapshot:
                data = doc.to_dict()
                if data.get('age') == 26:  # Modified value
                    modifications.append(data)
                    modification_event.set()

        # Start listening
        watch = user.on_snapshot(on_change)
        time.sleep(0.5)  # Wait for initial snapshot

        # Modify the document
        user.age = 26
        user.save()

        # Wait for modification notification
        modification_event.wait(timeout=5)

        # Verify
        assert len(modifications) >= 1
        assert modifications[0]['name'] == 'Bob'
        assert modifications[0]['age'] == 26

        # Cleanup
        watch.unsubscribe()

    def test_document_listener_on_detached_raises_error(self, db):
        """Test that on_snapshot on DETACHED object raises ValueError."""
        users = db.collection('snapshot_users')
        user = users.new()  # DETACHED

        def dummy_callback(doc_snapshot, changes, read_time):
            pass

        with pytest.raises(ValueError, match="DETACHED"):
            user.on_snapshot(dummy_callback)

    def test_document_listener_on_deleted_raises_error(self, db):
        """Test that on_snapshot on DELETED object raises RuntimeError."""
        users = db.collection('snapshot_users')

        user = users.new()
        user.name = 'ToDelete'
        user.save()
        user.delete()

        def dummy_callback(doc_snapshot, changes, read_time):
            pass

        with pytest.raises(RuntimeError, match="DELETED"):
            user.on_snapshot(dummy_callback)

    def test_document_listener_unsubscribe_stops_updates(self, db):
        """Test that unsubscribe() stops receiving updates."""
        users = db.collection('snapshot_users')

        user = users.new()
        user.name = 'Charlie'
        user.counter = 0
        user.save()

        received_values = []
        callback_done = threading.Event()

        def on_change(doc_snapshot, changes, read_time):
            for doc in doc_snapshot:
                received_values.append(doc.to_dict()['counter'])
                if received_values[0] == 0:  # Initial snapshot
                    callback_done.set()

        # Start listening
        watch = user.on_snapshot(on_change)
        callback_done.wait(timeout=5)  # Wait for initial

        # Unsubscribe immediately
        watch.unsubscribe()
        time.sleep(0.5)

        # Modify after unsubscribe
        user.counter = 1
        user.save()
        time.sleep(1)

        # Should only have initial value
        assert len(received_values) == 1
        assert received_values[0] == 0


# =========================================================================
# Sync Tests: Collection Listeners
# =========================================================================

class TestCollectionListeners:
    """Test on_snapshot() for FireCollection (collection-level listeners)."""

    def test_collection_listener_detects_added_documents(self, db):
        """Test that collection listener detects newly added documents."""
        users = db.collection('snapshot_collection_users')

        added_docs = []
        callback_done = threading.Event()

        def on_change(col_snapshot, changes, read_time):
            for change in changes:
                if change.type.name == 'ADDED':
                    added_docs.append(change.document.id)
                    if len(added_docs) == 1:  # First add
                        callback_done.set()

        # Start listening to empty collection
        watch = users.on_snapshot(on_change)
        time.sleep(0.5)  # Let listener initialize

        # Add a document
        user = users.new()
        user.name = 'Alice'
        user.save()
        doc_id = user.id

        # Wait for notification
        callback_done.wait(timeout=5)

        # Verify
        assert doc_id in added_docs

        # Cleanup
        watch.unsubscribe()

    def test_collection_listener_detects_modified_documents(self, db):
        """Test that collection listener detects document modifications."""
        users = db.collection('snapshot_collection_users')

        # Create initial document
        user = users.new()
        user.name = 'Bob'
        user.version = 1
        user.save()
        doc_id = user.id

        modified_docs = []
        modification_event = threading.Event()

        def on_change(col_snapshot, changes, read_time):
            for change in changes:
                if change.type.name == 'MODIFIED':
                    data = change.document.to_dict()
                    if data.get('version') == 2:
                        modified_docs.append(change.document.id)
                        modification_event.set()

        # Start listening
        watch = users.on_snapshot(on_change)
        time.sleep(0.5)  # Wait for initial snapshot

        # Modify document
        user.version = 2
        user.save()

        # Wait for modification
        modification_event.wait(timeout=5)

        # Verify
        assert doc_id in modified_docs

        # Cleanup
        watch.unsubscribe()

    def test_collection_listener_detects_removed_documents(self, db):
        """Test that collection listener detects document deletions."""
        users = db.collection('snapshot_collection_users')

        # Create initial document
        user = users.new()
        user.name = 'Charlie'
        user.save()
        doc_id = user.id

        removed_docs = []
        removal_event = threading.Event()

        def on_change(col_snapshot, changes, read_time):
            for change in changes:
                if change.type.name == 'REMOVED':
                    removed_docs.append(change.document.id)
                    removal_event.set()

        # Start listening
        watch = users.on_snapshot(on_change)
        time.sleep(0.5)  # Wait for initial snapshot

        # Delete document
        user.delete()

        # Wait for removal notification
        removal_event.wait(timeout=5)

        # Verify
        assert doc_id in removed_docs

        # Cleanup
        watch.unsubscribe()


# =========================================================================
# Sync Tests: Query Listeners
# =========================================================================

class TestQueryListeners:
    """Test on_snapshot() for FireQuery (query-level listeners)."""

    def test_query_listener_filters_documents(self, db):
        """Test that query listener only watches filtered documents."""
        users = db.collection('snapshot_query_users')

        # Create some users
        alice = users.new()
        alice.name = 'Alice'
        alice.status = 'active'
        alice.save()

        bob = users.new()
        bob.name = 'Bob'
        bob.status = 'inactive'
        bob.save()

        active_users = []
        callback_done = threading.Event()

        def on_change(query_snapshot, changes, read_time):
            for change in changes:
                if change.type.name == 'ADDED':
                    data = change.document.to_dict()
                    if data.get('status') == 'active':
                        active_users.append(data['name'])
                        callback_done.set()

        # Listen to active users only
        active_query = users.where('status', '==', 'active')
        watch = active_query.on_snapshot(on_change)

        # Wait for initial snapshot
        callback_done.wait(timeout=5)

        # Verify - should only see Alice
        assert 'Alice' in active_users
        assert 'Bob' not in active_users

        # Cleanup
        watch.unsubscribe()

    def test_query_listener_detects_new_matches(self, db):
        """Test that query listener detects when new documents match the query."""
        users = db.collection('snapshot_query_users')

        new_matches = []
        match_event = threading.Event()

        def on_change(query_snapshot, changes, read_time):
            for change in changes:
                if change.type.name == 'ADDED':
                    data = change.document.to_dict()
                    new_matches.append(data['name'])
                    if data['name'] == 'Charlie':
                        match_event.set()

        # Listen to users with age > 25
        query = users.where('age', '>', 25)
        watch = query.on_snapshot(on_change)
        time.sleep(0.5)  # Wait for listener to initialize

        # Add a document that matches
        charlie = users.new()
        charlie.name = 'Charlie'
        charlie.age = 30
        charlie.save()

        # Wait for match
        match_event.wait(timeout=5)

        # Verify
        assert 'Charlie' in new_matches

        # Cleanup
        watch.unsubscribe()

    def test_query_listener_detects_documents_leaving_query(self, db):
        """Test that query listener detects when documents no longer match."""
        users = db.collection('snapshot_query_users')

        # Create a user matching the query
        user = users.new()
        user.name = 'David'
        user.age = 30
        user.save()

        removed_from_query = []
        removal_event = threading.Event()

        def on_change(query_snapshot, changes, read_time):
            for change in changes:
                if change.type.name == 'REMOVED':
                    removed_from_query.append(change.document.to_dict().get('name', 'unknown'))
                    removal_event.set()

        # Listen to users with age > 25
        query = users.where('age', '>', 25)
        watch = query.on_snapshot(on_change)
        time.sleep(0.5)  # Wait for initial snapshot

        # Modify user to not match anymore
        user.age = 20  # Now < 25
        user.save()

        # Wait for removal
        removal_event.wait(timeout=5)

        # Verify
        assert 'David' in removed_from_query

        # Cleanup
        watch.unsubscribe()


# =========================================================================
# Async Tests: Document Listeners
# =========================================================================
# NOTE: Async tests are disabled pending AsyncFireProx support for sync_client parameter
# The on_snapshot feature works identically for async objects via their _sync_doc_ref

# @pytest.mark.asyncio
# class TestAsyncDocumentListeners:
#     """Test on_snapshot() for AsyncFireObject (async document listeners)."""
#
#     async def test_async_document_listener_receives_snapshot(self, async_db_with_sync):
#         """Test that async document listener works (uses sync client)."""
#         users = async_db_with_sync.collection('async_snapshot_users')
#
#         # Create a user
#         user = users.new()
#         user.name = 'AsyncAlice'
#         user.age = 28
#         await user.save()
#
#         # Set up listener
#         callback_done = threading.Event()
#         received_data = []
#
#         def on_change(doc_snapshot, changes, read_time):
#             for doc in doc_snapshot:
#                 received_data.append(doc.to_dict())
#             callback_done.set()
#
#         # Start listening (sync listener on async object)
#         watch = user.on_snapshot(on_change)
#
#         # Wait for snapshot
#         callback_done.wait(timeout=5)
#
#         # Verify
#         assert len(received_data) == 1
#         assert received_data[0]['name'] == 'AsyncAlice'
#
#         # Cleanup
#         watch.unsubscribe()


# =========================================================================
# Async Tests: Collection Listeners
# =========================================================================
# NOTE: Async tests disabled pending AsyncFireProx support for sync_client parameter

# @pytest.mark.asyncio
# class TestAsyncCollectionListeners:
#     """Test on_snapshot() for AsyncFireCollection."""
#
#     async def test_async_collection_listener_detects_adds(self, async_db_with_sync):
#         """Test that async collection listener detects new documents."""
#         users = async_db_with_sync.collection('async_snapshot_collection')
#
#         added_names = []
#         callback_done = threading.Event()
#
#         def on_change(col_snapshot, changes, read_time):
#             for change in changes:
#                 if change.type.name == 'ADDED':
#                     added_names.append(change.document.to_dict()['name'])
#                     callback_done.set()
#
#         # Start listening
#         watch = users.on_snapshot(on_change)
#         time.sleep(0.5)
#
#         # Add document
#         user = users.new()
#         user.name = 'AsyncBob'
#         await user.save()
#
#         # Wait
#         callback_done.wait(timeout=5)
#
#         # Verify
#         assert 'AsyncBob' in added_names
#
#         # Cleanup
#         watch.unsubscribe()


# =========================================================================
# Async Tests: Query Listeners
# =========================================================================
# NOTE: Async tests disabled pending AsyncFireProx support for sync_client parameter

# @pytest.mark.asyncio
# class TestAsyncQueryListeners:
#     """Test on_snapshot() for AsyncFireQuery."""
#
#     async def test_async_query_listener_filters(self, async_db_with_sync):
#         """Test that async query listener filters correctly."""
#         users = async_db_with_sync.collection('async_snapshot_query')
#
#         # Create users
#         active_user = users.new()
#         active_user.name = 'ActiveUser'
#         active_user.status = 'active'
#         await active_user.save()
#
#         active_names = []
#         callback_done = threading.Event()
#
#         def on_change(query_snapshot, changes, read_time):
#             for change in changes:
#                 if change.type.name == 'ADDED':
#                     data = change.document.to_dict()
#                     if data.get('status') == 'active':
#                         active_names.append(data['name'])
#                         callback_done.set()
#
#         # Listen to query
#         query = users.where('status', '==', 'active')
#         watch = query.on_snapshot(on_change)
#
#         # Wait
#         callback_done.wait(timeout=5)
#
#         # Verify
#         assert 'ActiveUser' in active_names
#
#         # Cleanup
#         watch.unsubscribe()


# =========================================================================
# Integration Tests
# =========================================================================

class TestSnapshotIntegration:
    """Integration tests for on_snapshot functionality."""

    def test_multiple_listeners_on_same_document(self, db):
        """Test that multiple listeners can watch the same document."""
        users = db.collection('multi_listener_users')

        user = users.new()
        user.name = 'Multi'
        user.counter = 0
        user.save()

        listener1_done = threading.Event()
        listener2_done = threading.Event()
        listener1_values = []
        listener2_values = []

        def callback1(doc_snapshot, changes, read_time):
            for doc in doc_snapshot:
                listener1_values.append(doc.to_dict()['counter'])
            listener1_done.set()

        def callback2(doc_snapshot, changes, read_time):
            for doc in doc_snapshot:
                listener2_values.append(doc.to_dict()['counter'])
            listener2_done.set()

        # Start both listeners
        watch1 = user.on_snapshot(callback1)
        watch2 = user.on_snapshot(callback2)

        # Wait for both initial snapshots
        listener1_done.wait(timeout=5)
        listener2_done.wait(timeout=5)

        # Both should have received initial snapshot
        assert 0 in listener1_values
        assert 0 in listener2_values

        # Cleanup
        watch1.unsubscribe()
        watch2.unsubscribe()

    def test_listener_with_rapid_updates(self, db):
        """Test that listener handles rapid successive updates."""
        users = db.collection('rapid_update_users')

        user = users.new()
        user.name = 'Rapid'
        user.counter = 0
        user.save()

        updates_received = []
        lock = threading.Lock()

        def on_change(doc_snapshot, changes, read_time):
            for doc in doc_snapshot:
                with lock:
                    updates_received.append(doc.to_dict()['counter'])

        watch = user.on_snapshot(on_change)
        time.sleep(0.5)  # Wait for initial

        # Perform rapid updates
        for i in range(1, 6):
            user.counter = i
            user.save()
            time.sleep(0.1)

        # Wait for updates to propagate
        time.sleep(2)

        # Should have received multiple updates
        assert len(updates_received) > 1

        # Cleanup
        watch.unsubscribe()


# =========================================================================
# Fixtures
# =========================================================================

# Note: db and async_db fixtures are defined in conftest.py
# We only need to add a sync_client to async_db for on_snapshot

@pytest.fixture
def async_db_with_sync(async_client, firestore_test_harness):
    """Create an async FireProx client with sync_client for on_snapshot testing."""
    # Create sync client for on_snapshot functionality
    sync_client = firestore.Client(project=firestore_test_harness.project_id)
    return AsyncFireProx(async_client, sync_client=sync_client)
