"""
AsyncFireProx: Main entry point for async FireProx usage.

This module provides the AsyncFireProx class, which serves as the primary interface
for users to interact with Firestore asynchronously through the FireProx API.
"""

from typing import Any, Dict

from google.cloud.firestore import AsyncClient as AsyncFirestoreClient

from .async_fire_collection import AsyncFireCollection
from .async_fire_object import AsyncFireObject
from .base_fireprox import BaseFireProx


class AsyncFireProx(BaseFireProx):
    """
    Main entry point for the async FireProx library.

    AsyncFireProx wraps the native google-cloud-firestore AsyncClient and provides
    a simplified, Pythonic interface for working with Firestore asynchronously.

    Usage Examples:
        # Initialize with a pre-configured native async client
        from google.cloud import firestore
        from fire_prox import AsyncFireProx

        native_client = firestore.AsyncClient(project='my-project')
        db = AsyncFireProx(native_client)

        # Access a document (ATTACHED state)
        user = db.doc('users/alovelace')
        await user.fetch()
        print(user.name)

        # Create a new document
        users = db.collection('users')
        new_user = users.new()
        new_user.name = 'Charles Babbage'
        new_user.year = 1791
        await new_user.save()

        # Update a document
        user = db.doc('users/alovelace')
        await user.fetch()
        user.year = 1816
        await user.save()

        # Delete a document
        await user.delete()
    """

    def __init__(self, client: AsyncFirestoreClient):
        """
        Initialize AsyncFireProx with a native async Firestore client.

        Args:
            client: A configured google.cloud.firestore.AsyncClient instance.
                   Authentication and project configuration should be handled
                   before creating this instance.

        Raises:
            TypeError: If client is not a google.cloud.firestore.AsyncClient.

        Example:
            from google.cloud import firestore
            from fire_prox import AsyncFireProx

            # Option 1: Default credentials
            native_client = firestore.AsyncClient()

            # Option 2: Explicit project
            native_client = firestore.AsyncClient(project='my-project-id')

            # Initialize AsyncFireProx
            db = AsyncFireProx(native_client)
        """
        if not isinstance(client, AsyncFirestoreClient):
            raise TypeError(
                f"client must be a google.cloud.firestore.AsyncClient, "
                f"got {type(client)}"
            )

        super().__init__(client)

            # Create companion sync client for lazy loading
        # Both clients point to the same Firestore backend
        from google.cloud import firestore
        self._sync_client = firestore.Client(
            project=client.project,
            database=client._database
        )

    # =========================================================================
    # Document Access
    # =========================================================================

    def doc(self, path: str) -> AsyncFireObject:
        """
        Get a reference to a document by its full path.

        Creates an AsyncFireObject in ATTACHED state. No data is fetched from
        Firestore until fetch() is called or an attribute is accessed (lazy loading).

        Args:
            path: The full document path, e.g., 'users/alovelace' or
                 'users/uid/posts/post123'. Must be a valid Firestore
                 document path with an even number of segments.

        Returns:
            An AsyncFireObject instance in ATTACHED state.

        Raises:
            ValueError: If path has an odd number of segments.

        Example:
            # Root-level document with lazy loading
            user = db.doc('users/alovelace')
            print(user.name)  # Triggers automatic fetch

            # Or explicit fetch
            user = db.doc('users/alovelace')
            await user.fetch()
            print(user.name)

            # Nested document (subcollection)
            post = db.doc('users/alovelace/posts/post123')
            await post.fetch()
        """
        return self._create_document_proxy(path, AsyncFireObject)

    def document(self, path: str) -> AsyncFireObject:
        """
        Alias for doc(). Get a reference to a document by its full path.

        Args:
            path: The full document path.

        Returns:
            An AsyncFireObject instance in ATTACHED state.
        """
        return self.doc(path)

    # =========================================================================
    # Collection Access
    # =========================================================================

    def collection(self, path: str) -> AsyncFireCollection:
        """
        Get a reference to a collection by its path.

        Creates an AsyncFireCollection wrapper around the native
        AsyncCollectionReference.

        Args:
            path: The collection path, e.g., 'users' or 'users/uid/posts'.
                 Must have an odd number of segments.

        Returns:
            An AsyncFireCollection instance.

        Raises:
            ValueError: If path has an even number of segments.

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
        return self._create_collection_proxy(path, AsyncFireCollection)

    def _get_document_kwargs(self, path: str) -> Dict[str, Any]:
        sync_doc_ref = self._sync_client.document(path)
        return {'sync_doc_ref': sync_doc_ref, 'sync_client': self._sync_client}

    def _get_collection_kwargs(self, path: str) -> Dict[str, Any]:
        return {'sync_client': self._sync_client}

    # Note: batch() and transaction() methods are inherited from BaseFireProx
