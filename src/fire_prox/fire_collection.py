"""
FireCollection: Interface for working with Firestore collections (synchronous).

This module provides the synchronous FireCollection class, which represents a
Firestore collection and provides methods for creating new documents and
querying existing ones.
"""

from typing import Optional, Iterator, Any
from google.cloud.firestore_v1.collection import CollectionReference
from .base_fire_collection import BaseFireCollection
from .fire_object import FireObject
from .state import State


class FireCollection(BaseFireCollection):
    """
    A wrapper around Firestore CollectionReference for document management (synchronous).

    FireCollection provides a simplified interface for creating new documents
    and querying collections. It serves as a factory for FireObject instances
    and (in Phase 2) will provide a lightweight query builder.

    This is the synchronous implementation.

    Usage Examples:
        # Get a collection
        users = db.collection('users')

        # Create a new document in DETACHED state
        new_user = users.new()
        new_user.name = 'Ada Lovelace'
        new_user.year = 1815
        new_user.save()

        # Create with explicit ID
        user = users.new()
        user.name = 'Charles Babbage'
        user.save(doc_id='cbabbage')

        # Phase 2: Query the collection
        query = users.where('year', '>', 1800).limit(10)
        for user in query.get():
            print(user.name)
    """

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

        Example:
            users = db.collection('users')
            user = users.new()  # DETACHED state
            user.name = 'Ada Lovelace'
            user.year = 1815
            user.save(doc_id='alovelace')  # Now LOADED
        """
        return FireObject(
            doc_ref=None,
            initial_state=State.DETACHED,
            parent_collection=self
        )

    def doc(self, doc_id: str) -> FireObject:
        """
        Get a reference to a specific document in this collection.

        Creates a FireObject in ATTACHED state pointing to a specific
        document. No data is fetched until an attribute is accessed
        (lazy loading).

        Args:
            doc_id: The document ID within this collection.

        Returns:
            A new FireObject instance in ATTACHED state.

        Example:
            users = db.collection('users')
            user = users.doc('alovelace')  # ATTACHED state
            print(user.name)  # Triggers fetch, transitions to LOADED
        """
        doc_ref = self._collection_ref.document(doc_id)
        return FireObject(
            doc_ref=doc_ref,
            initial_state=State.ATTACHED,
            parent_collection=self
        )

    # =========================================================================
    # Parent Property (Phase 2)
    # =========================================================================

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

        Phase 2.5 feature. Builds a lightweight query for common filtering
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
            for user in query.get():
                print(user.name)
        """
        from .fire_query import FireQuery
        from google.cloud.firestore_v1.base_query import FieldFilter

        # Create initial query with filter
        filter_obj = FieldFilter(field, op, value)
        native_query = self._collection_ref.where(filter=filter_obj)
        return FireQuery(native_query, parent_collection=self)

    def order_by(
        self,
        field: str,
        direction: str = 'ASCENDING'
    ) -> 'FireQuery':
        """
        Create a query with ordering.

        Phase 2.5 feature. Orders results by a field.

        Args:
            field: The field path to order by.
            direction: 'ASCENDING' or 'DESCENDING'. Default is 'ASCENDING'.

        Returns:
            A FireQuery instance for method chaining.
        """
        from .fire_query import FireQuery
        from google.cloud.firestore_v1 import Query as QueryClass

        # Convert direction string to constant
        if direction.upper() == 'ASCENDING':
            direction_const = QueryClass.ASCENDING
        elif direction.upper() == 'DESCENDING':
            direction_const = QueryClass.DESCENDING
        else:
            raise ValueError(f"Invalid direction: {direction}. Must be 'ASCENDING' or 'DESCENDING'")

        # Create query with ordering
        native_query = self._collection_ref.order_by(field, direction=direction_const)
        return FireQuery(native_query, parent_collection=self)

    def limit(self, count: int) -> 'FireQuery':
        """
        Create a query with a result limit.

        Phase 2.5 feature. Limits the number of results returned.

        Args:
            count: Maximum number of results to return.

        Returns:
            A FireQuery instance for method chaining.
        """
        from .fire_query import FireQuery

        if count <= 0:
            raise ValueError(f"Limit count must be positive, got {count}")

        # Create query with limit
        native_query = self._collection_ref.limit(count)
        return FireQuery(native_query, parent_collection=self)

    def select(self, *field_paths: str) -> 'FireQuery':
        """
        Create a query with field projection.

        Phase 4 Part 3 feature. Selects specific fields to return in query results.
        Returns vanilla dictionaries instead of FireObject instances.

        Args:
            *field_paths: One or more field paths to select.

        Returns:
            A FireQuery instance with projection applied.

        Example:
            # Select specific fields
            results = users.select('name', 'email').get()
            # Returns: [{'name': 'Alice', 'email': 'alice@example.com'}, ...]
        """
        from .fire_query import FireQuery

        if not field_paths:
            raise ValueError("select() requires at least one field path")

        # Create query with projection
        native_query = self._collection_ref.select(list(field_paths))
        return FireQuery(native_query, parent_collection=self, projection=field_paths)

    def get_all(self) -> Iterator[FireObject]:
        """
        Retrieve all documents in the collection.

        Phase 2.5 feature. Returns an iterator of all documents.

        Yields:
            FireObject instances in LOADED state for each document.

        Example:
            for user in users.get_all():
                print(f"{user.name}: {user.year}")
        """
        # Stream all documents from the collection
        for snapshot in self._collection_ref.stream():
            yield FireObject.from_snapshot(snapshot, parent_collection=self)

    # =========================================================================
    # Aggregation Methods (Phase 4 Part 5)
    # =========================================================================

    def count(self) -> int:
        """
        Count documents in the collection.

        Phase 4 Part 5 feature. Returns the total count of documents
        without fetching their data.

        Returns:
            The number of documents in the collection.

        Example:
            total = users.count()
            print(f"Total users: {total}")
        """
        from .fire_query import FireQuery
        # Use collection reference directly as a query for aggregation
        query = FireQuery(self._collection_ref, parent_collection=self)
        return query.count()

    def sum(self, field: str):
        """
        Sum a numeric field across all documents.

        Phase 4 Part 5 feature. Calculates the sum of a numeric field
        without fetching document data.

        Args:
            field: The field name to sum.

        Returns:
            The sum of the field values (int or float).

        Example:
            total_revenue = orders.sum('amount')
        """
        from .fire_query import FireQuery
        # Use collection reference directly as a query for aggregation
        query = FireQuery(self._collection_ref, parent_collection=self)
        return query.sum(field)

    def avg(self, field: str) -> float:
        """
        Average a numeric field across all documents.

        Phase 4 Part 5 feature. Calculates the average of a numeric field
        without fetching document data.

        Args:
            field: The field name to average.

        Returns:
            The average of the field values (float).

        Example:
            avg_rating = products.avg('rating')
        """
        from .fire_query import FireQuery
        # Use collection reference directly as a query for aggregation
        query = FireQuery(self._collection_ref, parent_collection=self)
        return query.avg(field)

    def aggregate(self, **aggregations):
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

            stats = users.aggregate(
                total=Count(),
                total_score=Sum('score'),
                avg_age=Avg('age')
            )
            # Returns: {'total': 42, 'total_score': 5000, 'avg_age': 28.5}
        """
        from .fire_query import FireQuery
        # Use collection reference directly as a query for aggregation
        query = FireQuery(self._collection_ref, parent_collection=self)
        return query.aggregate(**aggregations)
