"""
FireCollection: Interface for working with Firestore collections.

This module provides the FireCollection class, which represents a Firestore
collection and provides methods for creating new documents and querying
existing ones.
"""

from typing import Optional, AsyncIterator, Any
from google.cloud.firestore_v1.collection import CollectionReference
from .fire_object import FireObject
from .state import State


class FireCollection:
    """
    A wrapper around Firestore CollectionReference for document management.

    FireCollection provides a simplified interface for creating new documents
    and querying collections. It serves as a factory for FireObject instances
    and (in Phase 2) will provide a lightweight query builder.

    Attributes:
        _collection_ref: The underlying CollectionReference from
                        google-cloud-firestore.
        _client: Reference to the parent FireProx client instance.

    Usage Examples:
        # Get a collection
        users = db.collection('users')

        # Create a new document in DETACHED state
        new_user = users.new()
        new_user.name = 'Ada Lovelace'
        new_user.year = 1815
        await new_user.save()

        # Create with explicit ID
        user = users.new()
        user.name = 'Charles Babbage'
        await user.save(doc_id='cbabbage')

        # Phase 2: Query the collection
        query = users.where('year', '>', 1800).limit(10)
        async for user in await query.get():
            print(user.name)
    """

    def __init__(
        self,
        collection_ref: CollectionReference,
        client: Optional[Any] = None
    ):
        """
        Initialize a FireCollection.

        Args:
            collection_ref: The underlying CollectionReference from
                           google-cloud-firestore.
            client: Optional reference to the parent FireProx client.

        Note:
            This constructor is primarily used internally. Users typically
            create FireCollection instances via:
            - db.collection('collection_name')
            - user.collection('subcollection_name')  (Phase 2)
        """
        self._collection_ref = collection_ref
        self._client = client

    # =========================================================================
    # Document Creation
    # =========================================================================

    def new(self) -> FireObject:
        """
        Create a new FireObject in DETACHED state.

        Creates a new FireObject that exists only in memory. The object has
        no DocumentReference yet and will receive one when save() is called
        with an optional doc_id or auto-generated ID.

        Returns:
            A new FireObject instance in DETACHED state.

        Side Effects:
            Creates FireObject with:
            - _doc_ref = None
            - _state = State.DETACHED
            - _data = {} (empty)
            - _dirty = True (implicitly, as DETACHED is always dirty)
            - _parent_collection = self (for save() to use)

        Example:
            users = db.collection('users')
            user = users.new()  # DETACHED state
            user.name = 'Ada Lovelace'
            user.year = 1815
            await user.save(doc_id='alovelace')  # Now LOADED
        """
        raise NotImplementedError("Phase 1 stub")

    def doc(self, doc_id: str) -> FireObject:
        """
        Get a reference to a specific document in this collection.

        Creates a FireObject in ATTACHED state pointing to a specific
        document. No data is fetched until an attribute is accessed.

        Args:
            doc_id: The document ID within this collection.

        Returns:
            A new FireObject instance in ATTACHED state.

        Side Effects:
            Creates FireObject with:
            - _doc_ref = self._collection_ref.document(doc_id)
            - _state = State.ATTACHED
            - _data = {} (empty, will be loaded on access)
            - _dirty = False

        Example:
            users = db.collection('users')
            user = users.doc('alovelace')  # ATTACHED state
            print(user.name)  # Triggers fetch, transitions to LOADED
        """
        raise NotImplementedError("Phase 1 stub")

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def id(self) -> str:
        """
        Get the collection ID (last segment of collection path).

        Returns:
            The collection ID string.

        Example:
            users = db.collection('users')
            print(users.id)  # 'users'

            posts = user.collection('posts')
            print(posts.id)  # 'posts'
        """
        raise NotImplementedError("Phase 1 stub")

    @property
    def path(self) -> str:
        """
        Get the full Firestore path of the collection.

        Returns:
            The full path string (e.g., 'users' or 'users/uid/posts').

        Example:
            users = db.collection('users')
            print(users.path)  # 'users'

            posts = db.doc('users/alovelace').collection('posts')
            print(posts.path)  # 'users/alovelace/posts'
        """
        raise NotImplementedError("Phase 1 stub")

    @property
    def parent(self) -> Optional[FireObject]:
        """
        Get the parent document if this is a subcollection.

        Returns:
            FireObject representing the parent document if this is a
            subcollection, None if this is a root-level collection.

        Note:
            Phase 2 feature. Returns None in Phase 1 as subcollections
            are not yet implemented.

        Example:
            posts = db.doc('users/alovelace').collection('posts')
            parent = posts.parent
            print(parent.path)  # 'users/alovelace'
        """
        raise NotImplementedError("Phase 2 feature - subcollections")

    # =========================================================================
    # Query Methods (Phase 2)
    # =========================================================================

    def where(self, field: str, op: str, value: Any) -> 'FireQuery':
        """
        Create a query with a filter condition.

        Phase 2 feature. Builds a lightweight query for common filtering
        needs. For complex queries, users should use the native API and
        hydrate results with FireObject.from_snapshot().

        Args:
            field: The field path to filter on (e.g., 'name', 'address.city').
            op: Comparison operator: '==', '!=', '<', '<=', '>', '>=',
                'in', 'not-in', 'array-contains', 'array-contains-any'.
            value: The value to compare against.

        Returns:
            A FireQuery instance for method chaining.

        Example:
            query = users.where('birth_year', '>', 1800)
                        .where('country', '==', 'UK')
                        .limit(10)
            async for user in await query.get():
                print(user.name)
        """
        raise NotImplementedError("Phase 2 feature - querying")

    def order_by(
        self,
        field: str,
        direction: str = 'ASCENDING'
    ) -> 'FireQuery':
        """
        Create a query with ordering.

        Phase 2 feature. Orders results by a field.

        Args:
            field: The field path to order by.
            direction: 'ASCENDING' or 'DESCENDING'. Default is 'ASCENDING'.

        Returns:
            A FireQuery instance for method chaining.
        """
        raise NotImplementedError("Phase 2 feature - querying")

    def limit(self, count: int) -> 'FireQuery':
        """
        Create a query with a result limit.

        Phase 2 feature. Limits the number of results returned.

        Args:
            count: Maximum number of results to return.

        Returns:
            A FireQuery instance for method chaining.
        """
        raise NotImplementedError("Phase 2 feature - querying")

    async def get_all(self) -> AsyncIterator[FireObject]:
        """
        Retrieve all documents in the collection.

        Phase 2 feature. Returns an async iterator of all documents.

        Yields:
            FireObject instances in LOADED state for each document.

        Example:
            async for user in users.get_all():
                print(f"{user.name}: {user.year}")
        """
        raise NotImplementedError("Phase 2 feature - querying")

    # =========================================================================
    # Special Methods
    # =========================================================================

    def __repr__(self) -> str:
        """
        Return a detailed string representation for debugging.

        Returns:
            String showing collection path.

        Example:
            <FireCollection path='users'>
        """
        raise NotImplementedError("Phase 1 stub")

    def __str__(self) -> str:
        """
        Return a human-readable string representation.

        Returns:
            String showing the collection path.

        Example:
            'FireCollection(users)'
        """
        raise NotImplementedError("Phase 1 stub")
