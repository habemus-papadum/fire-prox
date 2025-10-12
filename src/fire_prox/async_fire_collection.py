"""
AsyncFireCollection: Async version of FireCollection.

This module implements the asynchronous FireCollection class for use with
google.cloud.firestore.AsyncClient.
"""

from typing import Optional, Any, AsyncIterator
from .base_fire_collection import BaseFireCollection
from .async_fire_object import AsyncFireObject
from .state import State


class AsyncFireCollection(BaseFireCollection):
    """
    A wrapper around Firestore AsyncCollectionReference for document management.

    AsyncFireCollection provides a simplified interface for creating new documents
    and querying collections asynchronously.

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
        async for user in query.get():
            print(user.name)
    """

    # =========================================================================
    # Document Creation
    # =========================================================================

    def new(self) -> AsyncFireObject:
        """
        Create a new AsyncFireObject in DETACHED state.

        Creates a new AsyncFireObject that exists only in memory. The object
        has no DocumentReference yet and will receive one when save() is called.

        Returns:
            A new AsyncFireObject instance in DETACHED state.

        Example:
            users = db.collection('users')
            user = users.new()  # DETACHED state
            user.name = 'Ada Lovelace'
            user.year = 1815
            await user.save(doc_id='alovelace')  # Now LOADED
        """
        return AsyncFireObject(
            doc_ref=None,
            initial_state=State.DETACHED,
            parent_collection=self
        )

    def doc(self, doc_id: str) -> AsyncFireObject:
        """
        Get a reference to a specific document in this collection.

        Creates an AsyncFireObject in ATTACHED state pointing to a specific
        document. No data is fetched until fetch() is called or an attribute is
        accessed (lazy loading).

        Args:
            doc_id: The document ID within this collection.

        Returns:
            A new AsyncFireObject instance in ATTACHED state.

        Example:
            users = db.collection('users')
            user = users.doc('alovelace')  # ATTACHED state
            print(user.name)  # Triggers automatic fetch (lazy loading)
        """
        # Create both async and sync doc refs
        async_doc_ref = self._collection_ref.document(doc_id)
        sync_doc_ref = None
        if self._sync_client:
            sync_collection_ref = self._sync_client.collection(self.path)
            sync_doc_ref = sync_collection_ref.document(doc_id)

        return AsyncFireObject(
            doc_ref=async_doc_ref,
            sync_doc_ref=sync_doc_ref,
            initial_state=State.ATTACHED,
            parent_collection=self
        )

    # =========================================================================
    # Properties (inherited from BaseFireCollection)
    # =========================================================================

    @property
    def parent(self) -> Optional[AsyncFireObject]:
        """
        Get the parent document if this is a subcollection.

        Phase 2 feature.

        Returns:
            AsyncFireObject representing the parent document if this is a
            subcollection, None if this is a root-level collection.
        """
        raise NotImplementedError("Phase 2 feature - subcollections")

    # =========================================================================
    # Query Methods (Phase 2)
    # =========================================================================

    def where(self, field: str, op: str, value: Any) -> 'AsyncFireQuery':
        """
        Create a query with a filter condition.

        Phase 2 feature. Builds a lightweight query for common filtering needs.

        Args:
            field: The field path to filter on.
            op: Comparison operator.
            value: The value to compare against.

        Returns:
            An AsyncFireQuery instance for method chaining.

        Example:
            query = users.where('birth_year', '>', 1800)
                        .where('country', '==', 'UK')
                        .limit(10)
            async for user in query.get():
                print(user.name)
        """
        raise NotImplementedError("Phase 2 feature - querying")

    def order_by(
        self,
        field: str,
        direction: str = 'ASCENDING'
    ) -> 'AsyncFireQuery':
        """
        Create a query with ordering.

        Phase 2 feature.

        Args:
            field: The field path to order by.
            direction: 'ASCENDING' or 'DESCENDING'.

        Returns:
            An AsyncFireQuery instance for method chaining.
        """
        raise NotImplementedError("Phase 2 feature - querying")

    def limit(self, count: int) -> 'AsyncFireQuery':
        """
        Create a query with a result limit.

        Phase 2 feature.

        Args:
            count: Maximum number of results to return.

        Returns:
            An AsyncFireQuery instance for method chaining.
        """
        raise NotImplementedError("Phase 2 feature - querying")

    async def get_all(self) -> AsyncIterator[AsyncFireObject]:
        """
        Retrieve all documents in the collection.

        Phase 2 feature. Returns an async iterator of all documents.

        Yields:
            AsyncFireObject instances in LOADED state for each document.

        Example:
            async for user in users.get_all():
                print(f"{user.name}: {user.year}")
        """
        raise NotImplementedError("Phase 2 feature - querying")
        # Unreachable, but for type checking:
        yield  # type: ignore
