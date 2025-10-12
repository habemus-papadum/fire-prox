"""
BaseFireProx: Shared logic for sync and async FireProx implementations.

This module contains the base class that implements all logic that is
identical between synchronous and asynchronous FireProx implementations.
"""

from typing import Any


class BaseFireProx:
    """
    Base class for FireProx implementations (sync and async).

    Contains all shared logic:
    - Client storage
    - Path validation
    - String representations

    Subclasses must implement:
    - doc() - creates FireObject/AsyncFireObject
    - collection() - creates FireCollection/AsyncFireCollection
    """

    def __init__(self, client: Any):
        """
        Initialize FireProx with a native Firestore client.

        Args:
            client: A configured google.cloud.firestore.Client or
                   google.cloud.firestore.AsyncClient instance.

        Note:
            Type checking is handled in subclasses since they know
            which client type to expect.
        """
        self._client = client

    # =========================================================================
    # Client Access (SHARED)
    # =========================================================================

    @property
    def native_client(self) -> Any:
        """
        Get the underlying google-cloud-firestore Client.

        Provides an "escape hatch" for users who need to perform operations
        not yet supported by FireProx or who want to use advanced native
        features like transactions, batched writes, or complex queries.

        Returns:
            The google.cloud.firestore.Client or AsyncClient instance.
        """
        return self._client

    @property
    def client(self) -> Any:
        """
        Alias for native_client. Get the underlying Firestore Client.

        Returns:
            The google.cloud.firestore.Client or AsyncClient instance.
        """
        return self._client

    # =========================================================================
    # Transaction Support (SHARED)
    # =========================================================================

    def transaction(self) -> Any:
        """
        Create a transaction for atomic read-modify-write operations.

        Returns the native Firestore transaction object that can be used
        with the @firestore.transactional decorator for synchronous operations
        or @firestore.async_transactional for asynchronous operations.

        This method provides a convenient way to create transactions without
        manually accessing the underlying client. The returned transaction
        object is a native Firestore Transaction that should be passed to
        functions decorated with @firestore.transactional.

        Returns:
            A native google.cloud.firestore.Transaction or
            google.cloud.firestore.AsyncTransaction instance.

        Example (Synchronous):
            transaction = db.transaction()

            @firestore.transactional
            def transfer_credits(transaction, from_id, to_id, amount):
                from_user = db.doc(f'users/{from_id}')
                to_user = db.doc(f'users/{to_id}')

                from_user.fetch(transaction=transaction)
                to_user.fetch(transaction=transaction)

                from_user.credits -= amount
                to_user.credits += amount

                from_user.save(transaction=transaction)
                to_user.save(transaction=transaction)

            transfer_credits(transaction, 'alice', 'bob', 100)

        Example (Asynchronous):
            transaction = db.transaction()

            @firestore.async_transactional
            async def transfer_credits(transaction, from_id, to_id, amount):
                from_user = db.doc(f'users/{from_id}')
                to_user = db.doc(f'users/{to_id}')

                await from_user.fetch(transaction=transaction)
                await to_user.fetch(transaction=transaction)

                from_user.credits -= amount
                to_user.credits += amount

                await from_user.save(transaction=transaction)
                await to_user.save(transaction=transaction)

            await transfer_credits(transaction, 'alice', 'bob', 100)
        """
        return self._client.transaction()

    def batch(self) -> Any:
        """
        Create a batch for accumulating multiple write operations.

        Returns the native Firestore WriteBatch object that can be used
        to accumulate write operations (set, update, delete) and commit
        them atomically in a single request.

        Unlike transactions, batches:
        - Do NOT support read operations
        - Do NOT require a decorator
        - Do NOT automatically retry on conflicts
        - DO guarantee operation order
        - ARE more efficient for bulk writes

        This method provides a convenient way to create batches without
        manually accessing the underlying client. The returned batch
        object is a native Firestore WriteBatch/AsyncWriteBatch.

        Returns:
            A native google.cloud.firestore.WriteBatch or
            google.cloud.firestore.AsyncWriteBatch instance.

        Example (Synchronous):
            batch = db.batch()

            # Accumulate operations
            user1 = db.doc('users/alice')
            user1.credits = 100
            user1.save(batch=batch)

            user2 = db.doc('users/bob')
            user2.delete(batch=batch)

            # Commit all operations atomically
            batch.commit()

        Example (Asynchronous):
            batch = db.batch()

            # Accumulate operations
            user1 = db.doc('users/alice')
            user1.credits = 100
            await user1.save(batch=batch)

            user2 = db.doc('users/bob')
            await user2.delete(batch=batch)

            # Commit all operations atomically
            await batch.commit()

        Example (Bulk Operations):
            batch = db.batch()
            users = db.collection('users')

            # Create multiple documents in one batch
            for i in range(100):
                user = users.doc(f'user{i}')
                user.name = f'User {i}'
                user.save(batch=batch)

            # All 100 documents created atomically
            batch.commit()

        Note:
            - Batches can contain up to 500 operations
            - All operations execute atomically (all-or-nothing)
            - Operations execute in the order added
            - Cannot save DETACHED documents in a batch
        """
        return self._client.batch()

    # =========================================================================
    # Utility Methods (SHARED)
    # =========================================================================

    def _validate_path(self, path: str, path_type: str) -> None:
        """
        Validate a Firestore path.

        Internal utility to ensure paths conform to Firestore requirements.

        Args:
            path: The path to validate.
            path_type: Either 'document' or 'collection' for error messages.

        Raises:
            ValueError: If path is invalid (wrong segment count, invalid
                       characters, empty segments, etc.).
        """
        if not path:
            raise ValueError(f"Path cannot be empty for {path_type}")

        # Split path into segments
        segments = path.split('/')

        # Check for empty segments
        if any(not segment for segment in segments):
            raise ValueError(f"Path cannot contain empty segments: '{path}'")

        # Validate segment count based on type
        num_segments = len(segments)
        if path_type == 'document':
            if num_segments % 2 != 0:
                raise ValueError(
                    f"Document path must have even number of segments, got {num_segments}: '{path}'"
                )
        elif path_type == 'collection':
            if num_segments % 2 != 1:
                raise ValueError(
                    f"Collection path must have odd number of segments, got {num_segments}: '{path}'"
                )

    # =========================================================================
    # Special Methods (SHARED)
    # =========================================================================

    def __repr__(self) -> str:
        """
        Return a detailed string representation for debugging.

        Returns:
            String showing the project ID and database.
        """
        project = getattr(self._client, 'project', 'unknown')
        return f"<{type(self).__name__} project='{project}' database='(default)'>"

    def __str__(self) -> str:
        """
        Return a human-readable string representation.

        Returns:
            String showing the project ID.
        """
        project = getattr(self._client, 'project', 'unknown')
        return f"{type(self).__name__}({project})"
