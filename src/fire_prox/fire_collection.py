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
        Create a query that projects documents to specific fields.

        Args:
            *field_paths: Field paths to include in the results.

        Returns:
            A FireQuery configured to return dictionaries containing only the
            requested fields. Document references within the projection are
            converted back into FireObject instances automatically.

        Example:
            query = users.select('name', 'country')
            for user in query.stream():
                print(user['name'])
        """
        from .fire_query import FireQuery

        if not field_paths:
            raise ValueError("select() requires at least one field path")

        native_query = self._collection_ref.select(field_paths)
        return FireQuery(
            native_query,
            parent_collection=self,
            selected_fields=tuple(field_paths)
        )

    def get_all(self) -> Iterator[FireObject]:
        """
        Retrieve all documents in the collection.

        Phase 2.5 feature. Returns an iterator of all documents.

        Note:
            To project documents to a subset of fields, use
            ``collection.select(...).get_all()``.

        Yields:
            FireObject instances in LOADED state for each document.

        Example:
            for user in users.get_all():
                print(f"{user.name}: {user.year}")
        """
        # Stream all documents from the collection
        for snapshot in self._collection_ref.stream():
            yield FireObject.from_snapshot(snapshot, parent_collection=self)
