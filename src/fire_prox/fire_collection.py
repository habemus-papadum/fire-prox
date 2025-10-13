"""Synchronous collection wrapper with optional schema typing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, Iterator, Optional, TypeVar, cast

from .base_fire_collection import BaseFireCollection
from .fire_object import FireObject
from .schema import SchemaMetadata
from .state import State

SchemaT = TypeVar("SchemaT", covariant=True)

if TYPE_CHECKING:
    from .fire_query import FireQuery
    from .typing_aliases import TypedFireObject


class FireCollection(BaseFireCollection[SchemaT], Generic[SchemaT]):
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

    def _instantiate_object(
        self,
        *,
        doc_ref: Any,
        initial_state: State,
        parent_collection: 'FireCollection',
        schema_type: Optional[type[SchemaT]] = None,
        schema_metadata: Optional[SchemaMetadata] = None,
        **_: Any,
    ) -> FireObject[SchemaT]:
        """Instantiate the synchronous FireObject wrapper."""
        return FireObject(
            doc_ref=doc_ref,
            initial_state=initial_state,
            parent_collection=parent_collection,
            schema_type=schema_type,
            schema_metadata=schema_metadata,
        )

    def new(self) -> 'TypedFireObject[SchemaT]':
        """Create a new FireObject in DETACHED state."""
        return cast('TypedFireObject[SchemaT]', super().new())

    def doc(self, doc_id: str) -> 'TypedFireObject[SchemaT]':
        """Get a reference to a specific document in this collection."""
        return cast('TypedFireObject[SchemaT]', super().doc(doc_id))

    def with_schema(self, schema: type[SchemaT]) -> 'FireCollection[SchemaT]':
        """Return a typed view of this collection."""

        return cast('FireCollection[SchemaT]', super().with_schema(schema))

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

    def where(self, field: str, op: str, value: Any) -> 'FireQuery[SchemaT]':
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
        from google.cloud.firestore_v1.base_query import FieldFilter

        from .fire_query import FireQuery

        # Create initial query with filter
        filter_obj = FieldFilter(field, op, value)
        native_query = self._collection_ref.where(filter=filter_obj)
        return FireQuery(native_query, parent_collection=self)

    def order_by(
        self,
        field: str,
        direction: str = 'ASCENDING'
    ) -> 'FireQuery[SchemaT]':
        """
        Create a query with ordering.

        Phase 2.5 feature. Orders results by a field.

        Args:
            field: The field path to order by.
            direction: 'ASCENDING' or 'DESCENDING'. Default is 'ASCENDING'.

        Returns:
            A FireQuery instance for method chaining.
        """
        from google.cloud.firestore_v1 import Query as QueryClass

        from .fire_query import FireQuery

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

    def limit(self, count: int) -> 'FireQuery[SchemaT]':
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

    def select(self, *field_paths: str) -> 'FireQuery[Any]':
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
    # Vector Query Methods
    # =========================================================================

    def find_nearest(
        self,
        vector_field: str,
        query_vector: Any,
        distance_measure: Any,
        limit: int,
        distance_result_field: Optional[str] = None,
    ) -> 'FireQuery':
        """
        Find the nearest neighbors based on vector similarity.

        Performs a vector similarity search to find documents with embeddings
        nearest to the query vector. Requires a single-field vector index on
        the vector_field.

        Args:
            vector_field: Name of the field containing vector embeddings.
            query_vector: Vector to compare against (google.cloud.firestore_v1.vector.Vector).
            distance_measure: Distance calculation method (DistanceMeasure.EUCLIDEAN,
                DistanceMeasure.COSINE, or DistanceMeasure.DOT_PRODUCT).
            limit: Maximum number of nearest neighbors to return (max 1000).
            distance_result_field: Optional field name to store the calculated distance
                in the query results.

        Returns:
            A FireQuery instance for method chaining and execution.

        Example:
            from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
            from google.cloud.firestore_v1.vector import Vector

            collection = db.collection("documents")
            query = collection.find_nearest(
                vector_field="embedding",
                query_vector=Vector([0.1, 0.2, 0.3]),
                distance_measure=DistanceMeasure.EUCLIDEAN,
                limit=5
            )
            for doc in query.get():
                print(f"{doc.title}: {doc.embedding}")

        Note:
            - Requires a vector index on the vector_field
            - Maximum limit is 1000 documents
            - Can be combined with where() for pre-filtering (requires composite index)
            - Does not work with Firestore emulator (production only)
        """
        from .fire_query import FireQuery

        # Create vector query using native find_nearest
        native_query = self._collection_ref.find_nearest(
            vector_field=vector_field,
            query_vector=query_vector,
            distance_measure=distance_measure,
            limit=limit,
            distance_result_field=distance_result_field,
        )
        return FireQuery(native_query, parent_collection=self)

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
