"""
FireQuery: Chainable query builder for Firestore (synchronous).

This module provides the synchronous FireQuery class, which wraps native
Firestore Query objects and provides a chainable interface for building and
executing queries.
"""

from typing import List, Iterator, Any, Optional
from google.cloud.firestore_v1.query import Query
from google.cloud.firestore_v1.base_query import FieldFilter
from .fire_object import FireObject


class FireQuery:
    """
    A chainable query builder for Firestore collections (synchronous).

    FireQuery wraps the native google-cloud-firestore Query object and provides
    a simplified, chainable interface for building and executing queries. It
    follows an immutable pattern - each method returns a new FireQuery instance
    with the modified query.

    This is the synchronous implementation. For async queries, use AsyncFireQuery.

    Usage Examples:
        # Basic filtering
        query = users.where('birth_year', '>', 1800)
        for user in query.get():
            print(user.name)

        # Chaining multiple conditions
        query = (users
                 .where('birth_year', '>', 1800)
                 .where('country', '==', 'England')
                 .order_by('birth_year')
                 .limit(10))
        for user in query.get():
            print(f"{user.name} - {user.birth_year}")

        # Stream results (generator)
        for user in users.where('active', '==', True).stream():
            print(user.name)

    Design Note:
        For complex queries beyond the scope of this builder (e.g., OR queries,
        advanced filtering), use the native Query API directly and hydrate results
        with FireObject.from_snapshot():

            native_query = client.collection('users').where(...)
            results = [FireObject.from_snapshot(snap) for snap in native_query.stream()]
    """

    def __init__(self, native_query: Query, parent_collection: Optional[Any] = None):
        """
        Initialize a FireQuery.

        Args:
            native_query: The underlying native Query object from google-cloud-firestore.
            parent_collection: Optional reference to parent FireCollection.
        """
        self._query = native_query
        self._parent_collection = parent_collection

    # =========================================================================
    # Query Building Methods (Immutable Pattern)
    # =========================================================================

    def where(self, field: str, op: str, value: Any) -> 'FireQuery':
        """
        Add a filter condition to the query.

        Creates a new FireQuery with an additional filter condition.
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
            A new FireQuery instance with the added filter.

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
        return FireQuery(new_query, self._parent_collection)

    def order_by(self, field: str, direction: str = 'ASCENDING') -> 'FireQuery':
        """
        Add an ordering clause to the query.

        Creates a new FireQuery with ordering by the specified field.

        Args:
            field: The field path to order by.
            direction: Sort direction. Either 'ASCENDING' or 'DESCENDING'.
                      Default is 'ASCENDING'.

        Returns:
            A new FireQuery instance with the ordering applied.

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
        return FireQuery(new_query, self._parent_collection)

    def limit(self, count: int) -> 'FireQuery':
        """
        Limit the number of results returned.

        Creates a new FireQuery that will return at most `count` results.

        Args:
            count: Maximum number of documents to return. Must be positive.

        Returns:
            A new FireQuery instance with the limit applied.

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
        return FireQuery(new_query, self._parent_collection)

    # =========================================================================
    # Query Execution Methods
    # =========================================================================

    def get(self) -> List[FireObject]:
        """
        Execute the query and return results as a list.

        Fetches all matching documents and hydrates them into FireObject
        instances in LOADED state.

        Returns:
            List of FireObject instances for all documents matching the query.
            Empty list if no documents match.

        Example:
            # Get all results as a list
            users = query.get()
            for user in users:
                print(f"{user.name}: {user.birth_year}")

            # Check if results exist
            results = query.get()
            if results:
                print(f"Found {len(results)} users")
            else:
                print("No users found")
        """
        # Execute query and hydrate results
        snapshots = self._query.stream()
        return [FireObject.from_snapshot(snap, self._parent_collection) for snap in snapshots]

    def stream(self) -> Iterator[FireObject]:
        """
        Execute the query and stream results as an iterator.

        Returns a generator that yields FireObject instances one at a time.
        This is more memory-efficient than .get() for large result sets
        as it doesn't load all results into memory at once.

        Yields:
            FireObject instances in LOADED state for each matching document.

        Example:
            # Stream results one at a time
            for user in query.stream():
                print(f"{user.name}: {user.birth_year}")
                # Process each user without loading all users into memory

            # Works with any query
            for post in (posts
                        .where('published', '==', True)
                        .order_by('date', direction='DESCENDING')
                        .stream()):
                print(post.title)
        """
        # Stream results and hydrate on-the-fly
        for snapshot in self._query.stream():
            yield FireObject.from_snapshot(snapshot, self._parent_collection)

    def __repr__(self) -> str:
        """Return string representation of the query."""
        return f"<FireQuery query={self._query}>"

    def __str__(self) -> str:
        """Return human-readable string representation."""
        return f"FireQuery({self._query})"
