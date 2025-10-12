"""
AsyncFireQuery: Chainable query builder for Firestore (asynchronous).

This module provides the asynchronous AsyncFireQuery class, which wraps native
Firestore AsyncQuery objects and provides a chainable interface for building and
executing async queries.
"""

from typing import Any, AsyncIterator, Dict, List, Optional, Union

from google.cloud.firestore_v1.async_document import AsyncDocumentReference
from google.cloud.firestore_v1.async_query import AsyncQuery
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1.document import DocumentReference

from .async_fire_object import AsyncFireObject


class AsyncFireQuery:
    """
    A chainable query builder for Firestore collections (asynchronous).

    AsyncFireQuery wraps the native google-cloud-firestore AsyncQuery object and
    provides a simplified, chainable interface for building and executing async
    queries. It follows an immutable pattern - each method returns a new
    AsyncFireQuery instance with the modified query.

    This is the asynchronous implementation. For sync queries, use FireQuery.

    Usage Examples:
        # Basic filtering
        query = users.where('birth_year', '>', 1800)
        results = await query.get()
        for user in results:
            print(user.name)

        # Chaining multiple conditions
        query = (users
                 .where('birth_year', '>', 1800)
                 .where('country', '==', 'England')
                 .order_by('birth_year')
                 .limit(10))
        async for user in query.stream():
            print(f"{user.name} - {user.birth_year}")

        # Async iteration
        async for user in users.where('active', '==', True).stream():
            print(user.name)

    Design Note:
        For complex queries beyond the scope of this builder (e.g., OR queries,
        advanced filtering), use the native AsyncQuery API directly and hydrate
        results with AsyncFireObject.from_snapshot():

            native_query = client.collection('users').where(...)
            results = [AsyncFireObject.from_snapshot(snap) async for snap in native_query.stream()]
    """

    def __init__(self, native_query: AsyncQuery, parent_collection: Optional[Any] = None, projection: Optional[tuple] = None):
        """
        Initialize an AsyncFireQuery.

        Args:
            native_query: The underlying native AsyncQuery object from google-cloud-firestore.
            parent_collection: Optional reference to parent AsyncFireCollection.
            projection: Optional tuple of field paths to project (select specific fields).
        """
        self._query = native_query
        self._parent_collection = parent_collection
        self._projection = projection

    # =========================================================================
    # Query Building Methods (Immutable Pattern)
    # =========================================================================

    def where(self, field: str, op: str, value: Any) -> 'AsyncFireQuery':
        """
        Add a filter condition to the query.

        Creates a new AsyncFireQuery with an additional filter condition.
        Uses the immutable pattern - returns a new instance rather than
        modifying the current query.

        Args:
            field: The field path to filter on (e.g., 'name', 'address.city').
            op: Comparison operator. Supported operators:
                '==' (equal), '!=' (not equal),
                '<' (less than), '<=' (less than or equal),
                '>' (greater than), '>=' (greater than or equal),
                'in' (value in list), 'not-in' (value not in list),
                'array-contains' (array contains value),
                'array-contains-any' (array contains any of the values).
            value: The value to compare against.

        Returns:
            A new AsyncFireQuery instance with the added filter.

        Example:
            # Single condition
            query = users.where('birth_year', '>', 1800)

            # Multiple conditions (chained)
            query = (users
                     .where('birth_year', '>', 1800)
                     .where('country', '==', 'England'))
        """
        # Create FieldFilter and add to query
        filter_obj = FieldFilter(field, op, value)
        new_query = self._query.where(filter=filter_obj)
        return AsyncFireQuery(new_query, self._parent_collection, self._projection)

    def order_by(self, field: str, direction: str = 'ASCENDING') -> 'AsyncFireQuery':
        """
        Add an ordering clause to the query.

        Creates a new AsyncFireQuery with ordering by the specified field.

        Args:
            field: The field path to order by.
            direction: Sort direction. Either 'ASCENDING' or 'DESCENDING'.
                      Default is 'ASCENDING'.

        Returns:
            A new AsyncFireQuery instance with the ordering applied.

        Example:
            # Ascending order
            query = users.order_by('birth_year')

            # Descending order
            query = users.order_by('birth_year', direction='DESCENDING')

            # Multiple orderings (chained)
            query = (users
                     .order_by('country')
                     .order_by('birth_year', direction='DESCENDING'))
        """
        # Convert direction string to Query constant
        if direction.upper() == 'ASCENDING':
            from google.cloud.firestore_v1 import Query as QueryClass
            direction_const = QueryClass.ASCENDING
        elif direction.upper() == 'DESCENDING':
            from google.cloud.firestore_v1 import Query as QueryClass
            direction_const = QueryClass.DESCENDING
        else:
            raise ValueError(f"Invalid direction: {direction}. Must be 'ASCENDING' or 'DESCENDING'")

        new_query = self._query.order_by(field, direction=direction_const)
        return AsyncFireQuery(new_query, self._parent_collection, self._projection)

    def limit(self, count: int) -> 'AsyncFireQuery':
        """
        Limit the number of results returned.

        Creates a new AsyncFireQuery that will return at most `count` results.

        Args:
            count: Maximum number of documents to return. Must be positive.

        Returns:
            A new AsyncFireQuery instance with the limit applied.

        Raises:
            ValueError: If count is not positive.

        Example:
            # Get top 10 results
            query = users.order_by('score', direction='DESCENDING').limit(10)

            # Get first 5 matching documents
            query = users.where('active', '==', True).limit(5)
        """
        if count <= 0:
            raise ValueError(f"Limit count must be positive, got {count}")

        new_query = self._query.limit(count)
        return AsyncFireQuery(new_query, self._parent_collection, self._projection)

    def start_at(self, *document_fields_or_snapshot) -> 'AsyncFireQuery':
        """
        Start query results at a cursor position (inclusive).

        Creates a new AsyncFireQuery that starts at the specified cursor. The cursor
        can be a document snapshot or a dictionary of field values matching the
        order_by fields.

        Args:
            *document_fields_or_snapshot: Either:
                - A dictionary of field values: {'field': value}
                - A DocumentSnapshot from a previous query
                - Direct field values matching order_by clause order

        Returns:
            A new AsyncFireQuery instance with the start cursor applied.

        Example:
            # Using field values (requires matching order_by)
            query = users.order_by('age').start_at({'age': 25})

            # Pagination: get first page, then start at last document
            page1 = await users.order_by('age').limit(10).get()
            last_age = page1[-1].age
            page2 = await users.order_by('age').start_at({'age': last_age}).limit(10).get()

            # Using a document snapshot
            last_doc_ref = page1[-1]._doc_ref
            last_snapshot = await last_doc_ref.get()
            page2 = await users.order_by('age').start_at(last_snapshot).limit(10).get()
        """
        new_query = self._query.start_at(*document_fields_or_snapshot)
        return AsyncFireQuery(new_query, self._parent_collection, self._projection)

    def start_after(self, *document_fields_or_snapshot) -> 'AsyncFireQuery':
        """
        Start query results after a cursor position (exclusive).

        Creates a new AsyncFireQuery that starts after the specified cursor. The cursor
        document itself is excluded from results. This is typically used for
        pagination to avoid duplicating the last document from the previous page.

        Args:
            *document_fields_or_snapshot: Either:
                - A dictionary of field values: {'field': value}
                - A DocumentSnapshot from a previous query
                - Direct field values matching order_by clause order

        Returns:
            A new AsyncFireQuery instance with the start-after cursor applied.

        Example:
            # Pagination: exclude the last document from previous page
            page1 = await users.order_by('age').limit(10).get()
            last_age = page1[-1].age
            page2 = await users.order_by('age').start_after({'age': last_age}).limit(10).get()

            # Using a document snapshot (common pattern)
            last_doc_ref = page1[-1]._doc_ref
            last_snapshot = await last_doc_ref.get()
            page2 = await users.order_by('age').start_after(last_snapshot).limit(10).get()
        """
        new_query = self._query.start_after(*document_fields_or_snapshot)
        return AsyncFireQuery(new_query, self._parent_collection, self._projection)

    def end_at(self, *document_fields_or_snapshot) -> 'AsyncFireQuery':
        """
        End query results at a cursor position (inclusive).

        Creates a new AsyncFireQuery that ends at the specified cursor. The cursor
        document is included in the results.

        Args:
            *document_fields_or_snapshot: Either:
                - A dictionary of field values: {'field': value}
                - A DocumentSnapshot
                - Direct field values matching order_by clause order

        Returns:
            A new AsyncFireQuery instance with the end cursor applied.

        Example:
            # Get all users up to and including age 50
            query = users.order_by('age').end_at({'age': 50})

            # Using a specific document as endpoint
            target_doc_ref = users.doc('user123')._doc_ref
            target_snapshot = await target_doc_ref.get()
            query = users.order_by('age').end_at(target_snapshot)
        """
        new_query = self._query.end_at(*document_fields_or_snapshot)
        return AsyncFireQuery(new_query, self._parent_collection, self._projection)

    def end_before(self, *document_fields_or_snapshot) -> 'AsyncFireQuery':
        """
        End query results before a cursor position (exclusive).

        Creates a new AsyncFireQuery that ends before the specified cursor. The cursor
        document itself is excluded from results.

        Args:
            *document_fields_or_snapshot: Either:
                - A dictionary of field values: {'field': value}
                - A DocumentSnapshot
                - Direct field values matching order_by clause order

        Returns:
            A new AsyncFireQuery instance with the end-before cursor applied.

        Example:
            # Get all users before age 50 (exclude 50)
            query = users.order_by('age').end_before({'age': 50})

            # Using a specific document as exclusive endpoint
            target_doc_ref = users.doc('user123')._doc_ref
            target_snapshot = await target_doc_ref.get()
            query = users.order_by('age').end_before(target_snapshot)
        """
        new_query = self._query.end_before(*document_fields_or_snapshot)
        return AsyncFireQuery(new_query, self._parent_collection, self._projection)

    def select(self, *field_paths: str) -> 'AsyncFireQuery':
        """
        Select specific fields to return (projection).

        Creates a new AsyncFireQuery that only returns the specified fields in the
        query results. When using projections, query results will be returned
        as vanilla dictionaries instead of AsyncFireObject instances. Any
        DocumentReferences in the returned dictionaries will be automatically
        converted to AsyncFireObject instances in ATTACHED state.

        Args:
            *field_paths: One or more field paths to select. Field paths can
                         include nested fields using dot notation (e.g., 'address.city').

        Returns:
            A new AsyncFireQuery instance with the projection applied.

        Raises:
            ValueError: If no field paths are provided.

        Example:
            # Select a single field
            query = users.select('name')
            results = await query.get()
            # Returns: [{'name': 'Alice'}, {'name': 'Bob'}, ...]

            # Select multiple fields
            query = users.select('name', 'email', 'birth_year')
            results = await query.get()
            # Returns: [{'name': 'Alice', 'email': 'alice@example.com', 'birth_year': 1990}, ...]

            # Select with filtering and ordering
            query = (users
                     .where('birth_year', '>', 1990)
                     .select('name', 'birth_year')
                     .order_by('birth_year')
                     .limit(10))

            # DocumentReferences are auto-converted to AsyncFireObjects
            query = posts.select('title', 'author')  # author is a DocumentReference
            results = await query.get()
            # results[0]['author'] is an AsyncFireObject, not a DocumentReference
            await results[0]['author'].fetch()
            print(results[0]['author'].name)

        Note:
            - Projection queries return dictionaries, not AsyncFireObject instances
            - Only the selected fields will be present in the returned dictionaries
            - DocumentReferences are automatically hydrated to AsyncFireObject instances
            - Projected results are more bandwidth-efficient for large documents
        """
        if not field_paths:
            raise ValueError("select() requires at least one field path")

        # Create new query with projection
        new_query = self._query.select(list(field_paths))
        return AsyncFireQuery(new_query, self._parent_collection, projection=field_paths)

    # =========================================================================
    # Aggregation Methods
    # =========================================================================

    async def count(self) -> int:
        """
        Count documents matching the query.

        Executes an aggregation query to count the number of documents that
        match the current query filters without fetching the actual documents.
        This is more efficient than fetching all documents and counting them.

        Returns:
            Integer count of matching documents. Returns 0 if no documents match.

        Example:
            # Count all users
            total_users = await users.count()
            # Returns: 150

            # Count with filters
            active_users = await users.where('active', '==', True).count()
            # Returns: 42

            # Count with complex query
            count = await (users
                          .where('age', '>', 25)
                          .where('country', '==', 'USA')
                          .count())
            # Returns: 37

        Note:
            This uses Firestore's native aggregation API, which is more efficient
            than fetching documents. However, it still counts as one document read
            per 1000 documents in the collection.
        """
        # Create async aggregation query using AsyncQuery's count method
        agg_query = self._query.count(alias='count')

        # Execute and extract result (await the async get method)
        result = await agg_query.get()
        if result and len(result) > 0:
            # Extract count from first (and only) aggregation result
            for agg_result in result:
                return agg_result[0].value
        return 0

    async def sum(self, field: str) -> Union[int, float]:
        """
        Sum a numeric field across all matching documents.

        Executes an aggregation query to sum the values of a specific field
        without fetching the actual documents. The field must contain numeric
        values (int or float).

        Args:
            field: Name of the numeric field to sum.

        Returns:
            Sum of the field values across all matching documents.
            Returns 0 if no documents match or if all values are null.

        Raises:
            ValueError: If field is None or empty.

        Example:
            # Sum all salaries
            total_salary = await employees.sum('salary')
            # Returns: 5000000

            # Sum with filters
            engineering_salary = await (employees
                                       .where('department', '==', 'Engineering')
                                       .sum('salary'))
            # Returns: 2500000

            # Sum revenue from active products
            total_revenue = await (products
                                  .where('active', '==', True)
                                  .sum('revenue'))
            # Returns: 1250000.50

        Note:
            - Null values are ignored in the sum
            - Non-numeric values will cause an error
            - This is more efficient than fetching all documents
        """
        if not field:
            raise ValueError("sum() requires a field name")

        # Create async aggregation query using AsyncQuery's sum method
        agg_query = self._query.sum(field, alias='sum')

        # Execute and extract result (await the async get method)
        result = await agg_query.get()
        if result and len(result) > 0:
            # Extract sum from first (and only) aggregation result
            for agg_result in result:
                return agg_result[0].value
        return 0

    async def avg(self, field: str) -> float:
        """
        Average a numeric field across all matching documents.

        Executes an aggregation query to calculate the arithmetic mean of a
        specific field without fetching the actual documents. The field must
        contain numeric values (int or float).

        Args:
            field: Name of the numeric field to average.

        Returns:
            Average of the field values across all matching documents.
            Returns 0.0 if no documents match or if all values are null.

        Raises:
            ValueError: If field is None or empty.

        Example:
            # Average age of all users
            avg_age = await users.avg('age')
            # Returns: 32.5

            # Average with filters
            avg_salary = await (employees
                               .where('department', '==', 'Engineering')
                               .avg('salary'))
            # Returns: 125000.0

            # Average rating for active products
            avg_rating = await (products
                               .where('active', '==', True)
                               .avg('rating'))
            # Returns: 4.2

        Note:
            - Null values are ignored in the average calculation
            - Non-numeric values will cause an error
            - This is more efficient than fetching all documents
        """
        if not field:
            raise ValueError("avg() requires a field name")

        # Create async aggregation query using AsyncQuery's avg method
        agg_query = self._query.avg(field, alias='avg')

        # Execute and extract result (await the async get method)
        result = await agg_query.get()
        if result and len(result) > 0:
            # Extract average from first (and only) aggregation result
            for agg_result in result:
                value = agg_result[0].value
                return value if value is not None else 0.0
        return 0.0

    async def aggregate(self, **aggregations) -> Dict[str, Any]:
        """
        Perform multiple aggregations in a single query.

        Executes an aggregation query with multiple aggregation operations
        (count, sum, average) without fetching the actual documents. This is
        more efficient than running multiple separate aggregation queries.

        Args:
            **aggregations: Named aggregations using Count(), Sum(field), or
                          Avg(field) from fire_prox.aggregation module.

        Returns:
            Dictionary mapping aggregation names to their results.

        Raises:
            ValueError: If no aggregations are provided or if invalid
                       aggregation types are used.

        Example:
            from fire_prox.aggregation import Count, Sum, Avg

            # Multiple aggregations in one query
            stats = await employees.aggregate(
                total_count=Count(),
                total_salary=Sum('salary'),
                avg_salary=Avg('salary'),
                avg_age=Avg('age')
            )
            # Returns: {
            #     'total_count': 150,
            #     'total_salary': 15000000,
            #     'avg_salary': 100000.0,
            #     'avg_age': 35.2
            # }

            # With filters
            eng_stats = await (employees
                              .where('department', '==', 'Engineering')
                              .aggregate(
                                  count=Count(),
                                  total_salary=Sum('salary')
                              ))
            # Returns: {'count': 50, 'total_salary': 5000000}

            # Financial dashboard
            financials = await (transactions
                               .where('date', '>=', start_date)
                               .aggregate(
                                   total_transactions=Count(),
                                   total_revenue=Sum('amount'),
                                   avg_transaction=Avg('amount')
                               ))

        Note:
            - Much more efficient than multiple separate aggregation queries
            - All aggregations execute in a single round-trip to Firestore
            - Null values are ignored in sum and average calculations
        """
        if not aggregations:
            raise ValueError("aggregate() requires at least one aggregation")

        from .aggregation import Avg, Count, Sum

        # Start with the first aggregation to create the AsyncAggregationQuery
        first_alias, first_agg_type = next(iter(aggregations.items()))

        if isinstance(first_agg_type, Count):
            agg_query = self._query.count(alias=first_alias)
        elif isinstance(first_agg_type, Sum):
            if not first_agg_type.field:
                raise ValueError(f"Sum aggregation '{first_alias}' is missing a field name")
            agg_query = self._query.sum(first_agg_type.field, alias=first_alias)
        elif isinstance(first_agg_type, Avg):
            if not first_agg_type.field:
                raise ValueError(f"Avg aggregation '{first_alias}' is missing a field name")
            agg_query = self._query.avg(first_agg_type.field, alias=first_alias)
        else:
            raise ValueError(
                f"Invalid aggregation type for '{first_alias}': {type(first_agg_type).__name__}. "
                f"Use Count(), Sum(field), or Avg(field)"
            )

        # Add remaining aggregations
        remaining_items = list(aggregations.items())[1:]
        for alias, agg_type in remaining_items:
            if isinstance(agg_type, Count):
                agg_query = agg_query.count(alias=alias)
            elif isinstance(agg_type, Sum):
                if not agg_type.field:
                    raise ValueError(f"Sum aggregation '{alias}' is missing a field name")
                agg_query = agg_query.sum(agg_type.field, alias=alias)
            elif isinstance(agg_type, Avg):
                if not agg_type.field:
                    raise ValueError(f"Avg aggregation '{alias}' is missing a field name")
                agg_query = agg_query.avg(agg_type.field, alias=alias)
            else:
                raise ValueError(
                    f"Invalid aggregation type for '{alias}': {type(agg_type).__name__}. "
                    f"Use Count(), Sum(field), or Avg(field)"
                )

        # Execute and extract results (await the async get method)
        results_dict = {}
        result = await agg_query.get()

        if result and len(result) > 0:
            for agg_result in result:
                # Extract all aggregation results by matching aliases
                for agg in agg_result:
                    value = agg.value
                    # Convert None to 0 for consistency
                    results_dict[agg.alias] = value if value is not None else 0

        return results_dict

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _convert_projection_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert DocumentReferences in projection data to AsyncFireObjects.

        Recursively processes a dictionary to convert any DocumentReference
        or AsyncDocumentReference instances to AsyncFireObject instances in
        ATTACHED state. This allows users to work with references naturally
        using the FireProx API.

        Args:
            data: Dictionary containing projection data from Firestore.

        Returns:
            Dictionary with DocumentReferences converted to AsyncFireObjects.
        """
        from .state import State

        result = {}
        for key, value in data.items():
            if isinstance(value, (DocumentReference, AsyncDocumentReference)):
                # Convert DocumentReference/AsyncDocumentReference to AsyncFireObject in ATTACHED state
                result[key] = AsyncFireObject(
                    doc_ref=value,
                    initial_state=State.ATTACHED,
                    parent_collection=self._parent_collection
                )
            elif isinstance(value, list):
                # Recursively process lists
                result[key] = [
                    AsyncFireObject(
                        doc_ref=item,
                        initial_state=State.ATTACHED,
                        parent_collection=self._parent_collection
                    ) if isinstance(item, (DocumentReference, AsyncDocumentReference))
                    else self._convert_projection_data(item) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            elif isinstance(value, dict):
                # Recursively process nested dictionaries
                result[key] = self._convert_projection_data(value)
            else:
                # Keep primitive values as-is
                result[key] = value
        return result

    # =========================================================================
    # Query Execution Methods
    # =========================================================================

    async def get(self) -> Union[List[AsyncFireObject], List[Dict[str, Any]]]:
        """
        Execute the query and return results as a list.

        Fetches all matching documents asynchronously and hydrates them into
        AsyncFireObject instances in LOADED state. If a projection is active
        (via .select()), returns vanilla dictionaries instead of AsyncFireObject
        instances.

        Returns:
            - If no projection: List of AsyncFireObject instances for all documents
              matching the query.
            - If projection active: List of dictionaries containing only the
              selected fields. DocumentReferences are converted to AsyncFireObjects.
            - Empty list if no documents match.

        Example:
            # Get all results as AsyncFireObjects
            users = await query.get()
            for user in users:
                print(f"{user.name}: {user.birth_year}")

            # Get projected results as dictionaries
            users = await query.select('name', 'email').get()
            for user_dict in users:
                print(f"{user_dict['name']}: {user_dict['email']}")

            # Check if results exist
            results = await query.get()
            if results:
                print(f"Found {len(results)} users")
            else:
                print("No users found")
        """
        # Execute query
        results = []

        # If projection is active, return vanilla dictionaries
        if self._projection:
            async for snap in self._query.stream():
                data = snap.to_dict()
                # Convert DocumentReferences to AsyncFireObjects
                converted_data = self._convert_projection_data(data)
                results.append(converted_data)
            return results

        # Otherwise, return AsyncFireObjects as usual
        async for snapshot in self._query.stream():
            obj = AsyncFireObject.from_snapshot(snapshot, self._parent_collection)
            results.append(obj)
        return results

    async def stream(self) -> Union[AsyncIterator[AsyncFireObject], AsyncIterator[Dict[str, Any]]]:
        """
        Execute the query and stream results as an async iterator.

        Returns an async generator that yields AsyncFireObject instances one at
        a time. This is more memory-efficient than .get() for large result sets
        as it doesn't load all results into memory at once. If a projection
        is active (via .select()), yields vanilla dictionaries instead.

        Yields:
            - If no projection: AsyncFireObject instances in LOADED state for each
              matching document.
            - If projection active: Dictionaries containing only the selected
              fields. DocumentReferences are converted to AsyncFireObjects.

        Example:
            # Stream results one at a time as AsyncFireObjects
            async for user in query.stream():
                print(f"{user.name}: {user.birth_year}")
                # Process each user without loading all users into memory

            # Stream projected results as dictionaries
            async for user_dict in query.select('name', 'email').stream():
                print(f"{user_dict['name']}: {user_dict['email']}")

            # Works with any query
            async for post in (posts
                              .where('published', '==', True)
                              .order_by('date', direction='DESCENDING')
                              .stream()):
                print(post.title)
        """
        # If projection is active, stream vanilla dictionaries
        if self._projection:
            async for snapshot in self._query.stream():
                data = snapshot.to_dict()
                # Convert DocumentReferences to AsyncFireObjects
                converted_data = self._convert_projection_data(data)
                yield converted_data
        else:
            # Otherwise, stream AsyncFireObjects as usual
            async for snapshot in self._query.stream():
                yield AsyncFireObject.from_snapshot(snapshot, self._parent_collection)

    # =========================================================================
    # Real-Time Listeners (Sync-only via sync_client)
    # =========================================================================

    def on_snapshot(self, callback: Any) -> Any:
        """
        Listen for real-time updates to this query.

        This method sets up a real-time listener that fires the callback
        whenever any document matching the query changes. The listener runs
        on a separate thread managed by the Firestore SDK.

        **Important**: This is a sync-only feature. Even for AsyncFireQuery,
        the listener uses a synchronous query (via the parent collection's
        _sync_client) to run on a background thread. This is the standard
        Firestore pattern for real-time listeners in Python.

        Args:
            callback: Callback function invoked on query changes.
                     Signature: callback(query_snapshot, changes, read_time)
                     - query_snapshot: List of DocumentSnapshot objects matching the query
                     - changes: List of DocumentChange objects (ADDED, MODIFIED, REMOVED)
                     - read_time: Timestamp of the snapshot

        Returns:
            Watch object with an `.unsubscribe()` method to stop listening.

        Example:
            import threading

            callback_done = threading.Event()

            def on_change(query_snapshot, changes, read_time):
                for change in changes:
                    if change.type.name == 'ADDED':
                        print(f"New: {change.document.id}")
                    elif change.type.name == 'MODIFIED':
                        print(f"Modified: {change.document.id}")
                    elif change.type.name == 'REMOVED':
                        print(f"Removed: {change.document.id}")
                callback_done.set()

            # Listen to active users only (async query)
            active_users = users.where('status', '==', 'active')
            watch = active_users.on_snapshot(on_change)

            # Wait for initial snapshot
            callback_done.wait()

            # Later: stop listening
            watch.unsubscribe()

        Note:
            The callback runs on a separate thread. Use threading primitives
            (Event, Lock, Queue) for synchronization with your main thread.
        """
        # Use the native async query's on_snapshot method
        # The Firestore SDK handles the threading internally
        return self._query.on_snapshot(callback)

    def __repr__(self) -> str:
        """Return string representation of the query."""
        return f"<AsyncFireQuery query={self._query}>"

    def __str__(self) -> str:
        """Return human-readable string representation."""
        return f"AsyncFireQuery({self._query})"
