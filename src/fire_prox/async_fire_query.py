"""
AsyncFireQuery: Chainable query builder for Firestore (asynchronous).

This module provides the asynchronous AsyncFireQuery class, which wraps native
Firestore AsyncQuery objects and provides a chainable interface for building and
executing async queries.
"""

from typing import List, AsyncIterator, Any, Optional
from google.cloud.firestore_v1.async_query import AsyncQuery
from google.cloud.firestore_v1.base_query import FieldFilter
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

    def __init__(self, native_query: AsyncQuery, parent_collection: Optional[Any] = None):
        """
        Initialize an AsyncFireQuery.

        Args:
            native_query: The underlying native AsyncQuery object from google-cloud-firestore.
            parent_collection: Optional reference to parent AsyncFireCollection.
        """
        self._query = native_query
        self._parent_collection = parent_collection

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
        return AsyncFireQuery(new_query, self._parent_collection)

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
        return AsyncFireQuery(new_query, self._parent_collection)

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
        return AsyncFireQuery(new_query, self._parent_collection)

    # =========================================================================
    # Query Execution Methods
    # =========================================================================

    async def get(self) -> List[AsyncFireObject]:
        """
        Execute the query and return results as a list.

        Fetches all matching documents asynchronously and hydrates them into
        AsyncFireObject instances in LOADED state.

        Returns:
            List of AsyncFireObject instances for all documents matching the query.
            Empty list if no documents match.

        Example:
            # Get all results as a list
            users = await query.get()
            for user in users:
                print(f"{user.name}: {user.birth_year}")

            # Check if results exist
            results = await query.get()
            if results:
                print(f"Found {len(results)} users")
            else:
                print("No users found")
        """
        # Execute query and hydrate results
        results = []
        async for snapshot in self._query.stream():
            obj = AsyncFireObject.from_snapshot(snapshot, self._parent_collection)
            results.append(obj)
        return results

    async def stream(self) -> AsyncIterator[AsyncFireObject]:
        """
        Execute the query and stream results as an async iterator.

        Returns an async generator that yields AsyncFireObject instances one at
        a time. This is more memory-efficient than .get() for large result sets
        as it doesn't load all results into memory at once.

        Yields:
            AsyncFireObject instances in LOADED state for each matching document.

        Example:
            # Stream results one at a time
            async for user in query.stream():
                print(f"{user.name}: {user.birth_year}")
                # Process each user without loading all users into memory

            # Works with any query
            async for post in (posts
                              .where('published', '==', True)
                              .order_by('date', direction='DESCENDING')
                              .stream()):
                print(post.title)
        """
        # Stream results and hydrate on-the-fly
        async for snapshot in self._query.stream():
            yield AsyncFireObject.from_snapshot(snapshot, self._parent_collection)

    def __repr__(self) -> str:
        """Return string representation of the query."""
        return f"<AsyncFireQuery query={self._query}>"

    def __str__(self) -> str:
        """Return human-readable string representation."""
        return f"AsyncFireQuery({self._query})"
