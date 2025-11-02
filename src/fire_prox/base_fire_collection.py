"""
BaseFireCollection: Shared logic for sync and async FireCollection implementations.

This module contains the base class that implements all logic that is
identical between synchronous and asynchronous FireCollection implementations.
"""

from typing import Any, Dict, Optional

from .state import State


class BaseFireCollection:
    """
    Base class for FireCollection implementations (sync and async).

    Contains all shared logic:
    - Initialization
    - Properties (id, path)
    - String representations

    Subclasses must implement:
    - _instantiate_object() - creates FireObject/AsyncFireObject
    - Query methods (Phase 2)
    """

    def __init__(
        self,
        collection_ref: Any,  # CollectionReference or AsyncCollectionReference
        client: Optional[Any] = None,
        sync_client: Optional[Any] = None
    ):
        """
        Initialize a FireCollection.

        Args:
            collection_ref: The underlying CollectionReference from
                           google-cloud-firestore.
            client: Optional reference to the parent FireProx client.
            sync_client: Optional sync Firestore client for lazy loading (async only).
        """
        self._collection_ref = collection_ref
        self._client = client
        self._sync_client = sync_client

    # =========================================================================
    # Document Factories (SHARED)
    # =========================================================================

    def _instantiate_object(
        self,
        *,
        doc_ref: Any,
        initial_state: State,
        parent_collection: 'BaseFireCollection',
        **kwargs: Any,
    ) -> Any:
        """Create a collection-backed document instance."""
        raise NotImplementedError

    def _get_new_kwargs(self) -> Dict[str, Any]:
        """Return extra kwargs for instantiating DETACHED objects."""
        return {}

    def _get_doc_kwargs(self, doc_id: str) -> Dict[str, Any]:
        """Return extra kwargs for instantiating ATTACHED objects."""
        return {}

    # -------------------------------------------------------------------------
    # Shared validation helpers
    # -------------------------------------------------------------------------

    def _validate_batch_size(self, batch_size: int) -> None:
        """
        Validate that a batch size is a positive integer.

        Args:
            batch_size: Proposed batch size to validate.

        Raises:
            ValueError: If batch_size is not a positive integer.
        """
        if batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {batch_size}")

    def new(self) -> Any:
        """Create a new document proxy in DETACHED state."""
        return self._instantiate_object(
            doc_ref=None,
            initial_state=State.DETACHED,
            parent_collection=self,
            **self._get_new_kwargs(),
        )

    def doc(self, doc_id: str) -> Any:
        """Create a document proxy in ATTACHED state."""
        doc_ref = self._collection_ref.document(doc_id)
        return self._instantiate_object(
            doc_ref=doc_ref,
            initial_state=State.ATTACHED,
            parent_collection=self,
            **self._get_doc_kwargs(doc_id),
        )

    # =========================================================================
    # Transaction Support (SHARED)
    # =========================================================================

    def transaction(self) -> Any:
        """
        Create a transaction for atomic read-modify-write operations.

        Convenience method for creating transactions directly from a collection
        reference, eliminating the need to access the root FireProx client.

        Returns:
            A native google.cloud.firestore.Transaction or
            google.cloud.firestore.AsyncTransaction instance.

        Example:
            users = db.collection('users')
            transaction = users.transaction()

            @firestore.transactional
            def update_user(transaction, user_id):
                user = users.doc(user_id)
                user.fetch(transaction=transaction)
                user.visits += 1
                user.save(transaction=transaction)

            update_user(transaction, 'alice')
        """
        return self._client.transaction()

    def batch(self) -> Any:
        """
        Create a batch for accumulating multiple write operations.

        Convenience method for creating batches directly from a collection
        reference, eliminating the need to access the root FireProx client.

        Returns:
            A native google.cloud.firestore.WriteBatch or
            google.cloud.firestore.AsyncWriteBatch instance.

        Example:
            users = db.collection('users')
            batch = users.batch()

            # Accumulate operations
            user1 = users.doc('alice')
            user1.name = 'Alice'
            user1.save(batch=batch)

            user2 = users.doc('bob')
            user2.name = 'Bob'
            user2.save(batch=batch)

            # Commit all operations atomically
            batch.commit()

        Note:
            See BaseFireProx.batch() for detailed documentation on batch operations.
        """
        return self._client.batch()

    # =========================================================================
    # Properties (SHARED)
    # =========================================================================

    @property
    def id(self) -> str:
        """
        Get the collection ID (last segment of collection path).

        Returns:
            The collection ID string.
        """
        return self._collection_ref.id

    @property
    def path(self) -> str:
        """
        Get the full Firestore path of the collection.

        Returns:
            The full path string (e.g., 'users' or 'users/uid/posts').
        """
        # _path is a tuple, convert to slash-separated string
        return '/'.join(self._collection_ref._path)

    # =========================================================================
    # Special Methods (SHARED)
    # =========================================================================

    def __repr__(self) -> str:
        """
        Return a detailed string representation for debugging.

        Returns:
            String showing collection path.
        """
        return f"<{type(self).__name__} path='{self.path}'>"

    def __str__(self) -> str:
        """
        Return a human-readable string representation.

        Returns:
            String showing the collection path.
        """
        return f"{type(self).__name__}({self.path})"

    # =========================================================================
    # Real-Time Listeners (Sync-only)
    # =========================================================================

    def on_snapshot(self, callback: Any) -> Any:
        """
        Listen for real-time updates to this collection.

        This method sets up a real-time listener that fires the callback
        whenever any document in the collection changes. The listener runs
        on a separate thread managed by the Firestore SDK.

        **Important**: This is a sync-only feature. Even for AsyncFireCollection
        instances, the listener uses the synchronous client (via _sync_client)
        to run on a background thread. This is the standard Firestore pattern
        for real-time listeners in Python.

        Args:
            callback: Callback function invoked on collection changes.
                     Signature: callback(col_snapshot, changes, read_time)
                     - col_snapshot: List of DocumentSnapshot objects
                     - changes: List of DocumentChange objects (ADDED, MODIFIED, REMOVED)
                     - read_time: Timestamp of the snapshot

        Returns:
            Watch object with an `.unsubscribe()` method to stop listening.

        Example:
            import threading

            callback_done = threading.Event()

            def on_change(col_snapshot, changes, read_time):
                for change in changes:
                    if change.type.name == 'ADDED':
                        print(f"New document: {change.document.id}")
                    elif change.type.name == 'MODIFIED':
                        print(f"Modified document: {change.document.id}")
                    elif change.type.name == 'REMOVED':
                        print(f"Removed document: {change.document.id}")
                callback_done.set()

            # Start listening to a collection
            users = db.collection('users')
            watch = users.on_snapshot(on_change)

            # Wait for initial snapshot
            callback_done.wait()

            # Later: stop listening
            watch.unsubscribe()

        Note:
            The callback runs on a separate thread. Use threading primitives
            (Event, Lock, Queue) for synchronization with your main thread.
        """
        # For sync FireCollection, use _collection_ref directly
        # For async FireCollection, use _sync_client to create sync ref
        if hasattr(self, '_sync_client') and self._sync_client is not None:
            # AsyncFireCollection: create sync collection ref
            collection_ref = self._sync_client.collection(self.path)
        else:
            # FireCollection: use regular collection ref
            collection_ref = self._collection_ref

        # Set up the listener
        return collection_ref.on_snapshot(callback)
