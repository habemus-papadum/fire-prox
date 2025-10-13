"""
AsyncFireCollection: Async version of FireCollection.

This module implements the asynchronous FireCollection class for use with
google.cloud.firestore.AsyncClient.
"""

from typing import Any, AsyncIterator, Optional

from .async_fire_object import AsyncFireObject
from .base_fire_collection import BaseFireCollection
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
            **self._build_object_kwargs(
                doc_ref=None,
                initial_state=State.DETACHED,
                sync_client=self._sync_client,
            )
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
        if self._sync_client and self._client:
            _, sync_doc_ref = self._client._paired_document_refs(f"{self.path}/{doc_id}")

        return AsyncFireObject(
            **self._build_object_kwargs(
                doc_ref=async_doc_ref,
                initial_state=State.ATTACHED,
                sync_doc_ref=sync_doc_ref,
                sync_client=self._sync_client,
            )
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

        Phase 2.5 feature. Builds a lightweight query for common filtering needs.

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
            async for user in query.stream():
                print(user.name)
        """
        from google.cloud.firestore_v1.base_query import FieldFilter

        from .async_fire_query import AsyncFireQuery

        # Create initial query with filter
        filter_obj = FieldFilter(field, op, value)
        native_query = self._collection_ref.where(filter=filter_obj)
        return AsyncFireQuery(native_query, parent_collection=self)

    def order_by(
        self,
        field: str,
        direction: str = 'ASCENDING'
    ) -> 'AsyncFireQuery':
        """
        Create a query with ordering.

        Phase 2.5 feature.

        Args:
            field: The field path to order by.
            direction: 'ASCENDING' or 'DESCENDING'.

        Returns:
            An AsyncFireQuery instance for method chaining.
        """
        from google.cloud.firestore_v1 import Query as QueryClass

        from .async_fire_query import AsyncFireQuery

        # Convert direction string to constant
        if direction.upper() == 'ASCENDING':
            direction_const = QueryClass.ASCENDING
        elif direction.upper() == 'DESCENDING':
            direction_const = QueryClass.DESCENDING
        else:
            raise ValueError(f"Invalid direction: {direction}. Must be 'ASCENDING' or 'DESCENDING'")

        # Create query with ordering
        native_query = self._collection_ref.order_by(field, direction=direction_const)
        return AsyncFireQuery(native_query, parent_collection=self)

    def limit(self, count: int) -> 'AsyncFireQuery':
        """
        Create a query with a result limit.

        Phase 2.5 feature.

        Args:
            count: Maximum number of results to return.

        Returns:
            An AsyncFireQuery instance for method chaining.
        """
        from .async_fire_query import AsyncFireQuery

        if count <= 0:
            raise ValueError(f"Limit count must be positive, got {count}")

        # Create query with limit
        native_query = self._collection_ref.limit(count)
        return AsyncFireQuery(native_query, parent_collection=self)

    def select(self, *field_paths: str) -> 'AsyncFireQuery':
        """
        Create a query with field projection.

        Phase 4 Part 3 feature. Selects specific fields to return in query results.
        Returns vanilla dictionaries instead of AsyncFireObject instances.

        Args:
            *field_paths: One or more field paths to select.

        Returns:
            An AsyncFireQuery instance with projection applied.

        Example:
            # Select specific fields
            results = await users.select('name', 'email').get()
            # Returns: [{'name': 'Alice', 'email': 'alice@example.com'}, ...]
        """
        from .async_fire_query import AsyncFireQuery

        if not field_paths:
            raise ValueError("select() requires at least one field path")

        # Create query with projection
        native_query = self._collection_ref.select(list(field_paths))
        return AsyncFireQuery(native_query, parent_collection=self, projection=field_paths)

    async def get_all(self) -> AsyncIterator[AsyncFireObject]:
        """
        Retrieve all documents in the collection.

        Phase 2.5 feature. Returns an async iterator of all documents.

        Yields:
            AsyncFireObject instances in LOADED state for each document.

        Example:
            async for user in users.get_all():
                print(f"{user.name}: {user.year}")
        """
        # Stream all documents from the collection
        async for snapshot in self._collection_ref.stream():
            yield AsyncFireObject.from_snapshot(snapshot, parent_collection=self)

    # =========================================================================
    # Aggregation Methods (Phase 4 Part 5)
    # =========================================================================

    async def count(self) -> int:
        """
        Count documents in the collection.

        Phase 4 Part 5 feature. Returns the total count of documents
        without fetching their data.

        Returns:
            The number of documents in the collection.

        Example:
            total = await users.count()
            print(f"Total users: {total}")
        """
        from .async_fire_query import AsyncFireQuery
        # Use collection reference directly as a query for aggregation
        query = AsyncFireQuery(self._collection_ref, parent_collection=self)
        return await query.count()

    async def sum(self, field: str):
        """
        Sum a numeric field across all documents.

        Phase 4 Part 5 feature. Calculates the sum of a numeric field
        without fetching document data.

        Args:
            field: The field name to sum.

        Returns:
            The sum of the field values (int or float).

        Example:
            total_revenue = await orders.sum('amount')
        """
        from .async_fire_query import AsyncFireQuery
        # Use collection reference directly as a query for aggregation
        query = AsyncFireQuery(self._collection_ref, parent_collection=self)
        return await query.sum(field)

    async def avg(self, field: str) -> float:
        """
        Average a numeric field across all documents.

        Phase 4 Part 5 feature. Calculates the average of a numeric field
        without fetching document data.

        Args:
            field: The field name to average.

        Returns:
            The average of the field values (float).

        Example:
            avg_rating = await products.avg('rating')
        """
        from .async_fire_query import AsyncFireQuery
        # Use collection reference directly as a query for aggregation
        query = AsyncFireQuery(self._collection_ref, parent_collection=self)
        return await query.avg(field)

    async def aggregate(self, **aggregations):
        """
        Execute multiple aggregations in a single query.

        Phase 4 Part 5 feature. Performs multiple aggregation operations
        (count, sum, avg) in one efficient query.

        Args:
            **aggregations: Named aggregation operations using Count(), Sum(), or Avg().

        Returns:
            Dictionary mapping aggregation names to their results.

        Example:
            from fire_prox import Count, Sum, Avg

            stats = await users.aggregate(
                total=Count(),
                total_score=Sum('score'),
                avg_age=Avg('age')
            )
            # Returns: {'total': 42, 'total_score': 5000, 'avg_age': 28.5}
        """
        from .async_fire_query import AsyncFireQuery
        # Use collection reference directly as a query for aggregation
        query = AsyncFireQuery(self._collection_ref, parent_collection=self)
        return await query.aggregate(**aggregations)
