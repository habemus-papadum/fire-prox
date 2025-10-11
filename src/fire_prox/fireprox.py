"""
FireProx: Main entry point for the library.

This module provides the FireProx class, which serves as the primary interface
for users to interact with Firestore through the simplified FireProx API.
"""

from typing import Optional
from google.cloud.firestore import Client as FirestoreClient
from .fire_object import FireObject
from .fire_collection import FireCollection
from .state import State


class FireProx:
    """
    Main entry point for the FireProx library.

    FireProx wraps the native google-cloud-firestore Client and provides a
    simplified, Pythonic interface for working with Firestore. It delegates
    authentication and client configuration to the official library while
    providing higher-level abstractions for document and collection access.

    The design philosophy is "wrap, don't replace" - FireProx leverages the
    reliability and security of the native client while providing a more
    intuitive developer experience optimized for rapid prototyping.

    Attributes:
        _client: The underlying google.cloud.firestore.Client instance.

    Usage Examples:
        # Initialize with a pre-configured native client
        from google.cloud import firestore
        from fireprox import FireProx

        native_client = firestore.Client(project='my-project')
        db = FireProx(native_client)

        # Access a document (ATTACHED state, lazy loading)
        user = db.doc('users/alovelace')
        print(user.name)  # Automatically fetches data

        # Create a new document
        users = db.collection('users')
        new_user = users.new()
        new_user.name = 'Charles Babbage'
        new_user.year = 1791
        await new_user.save()

        # Update a document
        user = db.doc('users/alovelace')
        user.year = 1816
        await user.save()

        # Delete a document
        await user.delete()
    """

    def __init__(self, client: FirestoreClient):
        """
        Initialize FireProx with a native Firestore client.

        Args:
            client: A configured google.cloud.firestore.Client instance.
                   Authentication and project configuration should be handled
                   before creating this instance.

        Raises:
            TypeError: If client is not a google.cloud.firestore.Client instance.
            ValueError: If client is not properly configured.

        Example:
            from google.cloud import firestore
            from fireprox import FireProx

            # Option 1: Default credentials
            native_client = firestore.Client()

            # Option 2: Explicit project
            native_client = firestore.Client(project='my-project-id')

            # Option 3: Service account
            native_client = firestore.Client.from_service_account_json(
                'path/to/credentials.json'
            )

            # Initialize FireProx
            db = FireProx(native_client)
        """
        raise NotImplementedError("Phase 1 stub")

    # =========================================================================
    # Document Access
    # =========================================================================

    def doc(self, path: str) -> FireObject:
        """
        Get a reference to a document by its full path.

        Creates a FireObject in ATTACHED state. No data is fetched from
        Firestore until an attribute is accessed (lazy loading).

        Args:
            path: The full document path, e.g., 'users/alovelace' or
                 'users/uid/posts/post123'. Must be a valid Firestore
                 document path with an even number of segments.

        Returns:
            A FireObject instance in ATTACHED state.

        Raises:
            ValueError: If path has an odd number of segments (invalid
                       document path) or contains invalid characters.

        Side Effects:
            Creates FireObject with:
            - _doc_ref = self._client.document(path)
            - _state = State.ATTACHED
            - _data = {} (empty, lazy loaded)
            - _dirty = False

        Example:
            # Root-level document
            user = db.doc('users/alovelace')

            # Nested document (subcollection)
            post = db.doc('users/alovelace/posts/post123')

            # Lazy loading
            print(user.name)  # Triggers fetch on first access
        """
        raise NotImplementedError("Phase 1 stub")

    def document(self, path: str) -> FireObject:
        """
        Alias for doc(). Get a reference to a document by its full path.

        Provided for API consistency with the native library and user
        preference. Functionally identical to doc().

        Args:
            path: The full document path.

        Returns:
            A FireObject instance in ATTACHED state.
        """
        raise NotImplementedError("Phase 1 stub")

    # =========================================================================
    # Collection Access
    # =========================================================================

    def collection(self, path: str) -> FireCollection:
        """
        Get a reference to a collection by its path.

        Creates a FireCollection wrapper around the native CollectionReference.
        Used for creating new documents or (in Phase 2) querying.

        Args:
            path: The collection path, e.g., 'users' or 'users/uid/posts'.
                 Can be a root-level collection (odd number of segments) or
                 a subcollection path.

        Returns:
            A FireCollection instance.

        Raises:
            ValueError: If path has an even number of segments (invalid
                       collection path) or contains invalid characters.

        Side Effects:
            Creates FireCollection with:
            - _collection_ref = self._client.collection(path)
            - _client = self

        Example:
            # Root-level collection
            users = db.collection('users')
            new_user = users.new()
            new_user.name = 'Ada'
            await new_user.save()

            # Subcollection
            posts = db.collection('users/alovelace/posts')
            new_post = posts.new()
            new_post.title = 'Analysis Engine'
            await new_post.save()
        """
        raise NotImplementedError("Phase 1 stub")

    # =========================================================================
    # Client Access
    # =========================================================================

    @property
    def native_client(self) -> FirestoreClient:
        """
        Get the underlying google-cloud-firestore Client.

        Provides an "escape hatch" for users who need to perform operations
        not yet supported by FireProx or who want to use advanced native
        features like transactions, batched writes, or complex queries.

        Returns:
            The google.cloud.firestore.Client instance passed during init.

        Example:
            # Use native API for complex queries
            from google.cloud.firestore_v1.base_query import FieldFilter

            native_query = db.native_client.collection('users').where(
                filter=FieldFilter('year', 'in', [1815, 1843, 1852])
            )

            # Hydrate results into FireObjects
            results = [FireObject.from_snapshot(snap)
                      for snap in native_query.stream()]

            # Use native API for transactions
            transaction = db.native_client.transaction()
            # ... perform transactional operations ...
        """
        raise NotImplementedError("Phase 1 stub")

    @property
    def client(self) -> FirestoreClient:
        """
        Alias for native_client. Get the underlying Firestore Client.

        Provided for convenience. Functionally identical to native_client.

        Returns:
            The google.cloud.firestore.Client instance.
        """
        raise NotImplementedError("Phase 1 stub")

    # =========================================================================
    # Batch Operations (Phase 2+)
    # =========================================================================

    def batch(self) -> 'FireBatch':
        """
        Create a batch for atomic write operations.

        Phase 2+ feature. Provides a Pythonic wrapper around the native
        WriteBatch for performing multiple write operations atomically.

        Returns:
            A FireBatch instance for batching operations.

        Example:
            batch = db.batch()
            user1 = db.doc('users/user1')
            user1.status = 'active'
            batch.set(user1)

            user2 = db.doc('users/user2')
            batch.delete(user2)

            await batch.commit()
        """
        raise NotImplementedError("Phase 2+ feature - batch operations")

    def transaction(self) -> 'FireTransaction':
        """
        Create a transaction for atomic read-modify-write operations.

        Phase 2+ feature. Provides a Pythonic wrapper around the native
        Transaction for ensuring data consistency.

        Returns:
            A FireTransaction instance.

        Example:
            @db.transactional
            async def transfer_credits(from_user, to_user, amount):
                from_doc = db.doc(f'users/{from_user}')
                to_doc = db.doc(f'users/{to_user}')

                from_doc.credits -= amount
                to_doc.credits += amount

                await from_doc.save()
                await to_doc.save()
        """
        raise NotImplementedError("Phase 2+ feature - transactions")

    # =========================================================================
    # Utility Methods
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

        Implementation Notes:
            Firestore paths have specific requirements:
            - Document paths must have even number of segments
            - Collection paths must have odd number of segments
            - Segments cannot be empty
            - Segments cannot contain certain characters (/, etc.)
            - Total path length cannot exceed limits
        """
        raise NotImplementedError("Phase 1 stub")

    # =========================================================================
    # Special Methods
    # =========================================================================

    def __repr__(self) -> str:
        """
        Return a detailed string representation for debugging.

        Returns:
            String showing the project ID and database.

        Example:
            <FireProx project='my-project' database='(default)'>
        """
        raise NotImplementedError("Phase 1 stub")

    def __str__(self) -> str:
        """
        Return a human-readable string representation.

        Returns:
            String showing the project ID.

        Example:
            'FireProx(my-project)'
        """
        raise NotImplementedError("Phase 1 stub")
