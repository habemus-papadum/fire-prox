"""
FireProx: Main entry point for the library (synchronous).

This module provides the synchronous FireProx class, which serves as the primary
interface for users to interact with Firestore through the simplified FireProx API.
"""

from typing import overload

from google.cloud.firestore import Client as FirestoreClient

from ._typing import SchemaT, SchemaType
from .base_fireprox import BaseFireProx
from .fire_collection import FireCollection
from .fire_object import FireObject


class FireProx(BaseFireProx):
    """
    Main entry point for the FireProx library (synchronous).

    FireProx wraps the native google-cloud-firestore Client and provides a
    simplified, Pythonic interface for working with Firestore. It delegates
    authentication and client configuration to the official library while
    providing higher-level abstractions for document and collection access.

    The design philosophy is "wrap, don't replace" - FireProx leverages the
    reliability and security of the native client while providing a more
    intuitive developer experience optimized for rapid prototyping.

    This is the synchronous implementation that supports lazy loading.

    Usage Examples:
        # Initialize with a pre-configured native client
        from google.cloud import firestore
        from fire_prox import FireProx

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
        new_user.save()

        # Update a document
        user = db.doc('users/alovelace')
        user.year = 1816
        user.save()

        # Delete a document
        user.delete()
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

        Example:
            from google.cloud import firestore
            from fire_prox import FireProx

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
        # Type checking for sync client
        if not isinstance(client, FirestoreClient):
            raise TypeError(
                f"client must be a google.cloud.firestore.Client, got {type(client)}"
            )

        # Initialize base class
        super().__init__(client)

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

        Example:
            # Root-level document
            user = db.doc('users/alovelace')

            # Nested document (subcollection)
            post = db.doc('users/alovelace/posts/post123')

            # Lazy loading
            print(user.name)  # Triggers fetch on first access
        """
        return self._create_document_proxy(path, FireObject)

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
        return self.doc(path)

    # =========================================================================
    # Collection Access
    # =========================================================================

    @overload
    def collection(self, path: str) -> FireCollection[object]:
        ...

    @overload
    def collection(self, path: str, schema: SchemaType[SchemaT]) -> FireCollection[SchemaT]:
        ...

    def collection(
        self,
        path: str,
        schema: SchemaType[SchemaT] | None = None,
    ) -> FireCollection[SchemaT]:
        """
        Get a reference to a collection by its path.

        Creates a FireCollection wrapper around the native CollectionReference.
        Used for creating new documents or (in Phase 2) querying.

        Args:
            path: The collection path, e.g., 'users' or 'users/uid/posts'.
                 Can be a root-level collection (odd number of segments) or
                 a subcollection path.

        Args:
            schema: Optional dataclass schema to bind immediately. When provided,
                the returned collection and its documents expose
                ``FireObject[schema]`` to static type checkers.

        Returns:
            A FireCollection instance, typed when ``schema`` is supplied.

        Raises:
            ValueError: If path has an even number of segments (invalid
                       collection path) or contains invalid characters.

        Example:
            # Root-level collection
            users = db.collection('users')
            new_user = users.new()
            new_user.name = 'Ada'
            new_user.save()

            # Subcollection
            posts = db.collection('users/alovelace/posts')
            new_post = posts.new()
            new_post.title = 'Analysis Engine'
            new_post.save()
        """
        return self._create_collection_proxy(path, FireCollection, schema)

    # Note: batch() and transaction() methods are inherited from BaseFireProx
