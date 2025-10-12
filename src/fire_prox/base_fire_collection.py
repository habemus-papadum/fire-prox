"""
BaseFireCollection: Shared logic for sync and async FireCollection implementations.

This module contains the base class that implements all logic that is
identical between synchronous and asynchronous FireCollection implementations.
"""

from typing import Optional, Any


class BaseFireCollection:
    """
    Base class for FireCollection implementations (sync and async).

    Contains all shared logic:
    - Initialization
    - Properties (id, path)
    - String representations

    Subclasses must implement:
    - new() - creates FireObject/AsyncFireObject
    - doc() - creates FireObject/AsyncFireObject
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
