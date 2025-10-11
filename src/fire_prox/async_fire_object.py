"""
AsyncFireObject: Async version of FireObject for AsyncClient.

This module implements the asynchronous FireObject class for use with
google.cloud.firestore.AsyncClient.
"""

from typing import Any, Optional
from google.cloud.firestore_v1.async_document import AsyncDocumentReference
from google.cloud.firestore_v1.document import DocumentSnapshot
from google.cloud.exceptions import NotFound
from .base_fire_object import BaseFireObject
from .state import State


class AsyncFireObject(BaseFireObject):
    """
    Asynchronous schemaless, state-aware proxy for a Firestore document.

    AsyncFireObject provides an object-oriented interface to Firestore documents
    using the async/await pattern for all I/O operations.

    Note: Unlike the synchronous FireObject, AsyncFireObject does NOT support
    lazy loading via __getattr__ (Python doesn't support async __getattr__).
    Users must explicitly call `await obj.fetch()` before accessing attributes.

    Usage Examples:
        # Create a new document (DETACHED state)
        user = collection.new()
        user.name = 'Ada Lovelace'
        user.year = 1815
        await user.save()  # Transitions to LOADED

        # Load existing document
        user = db.doc('users/alovelace')  # ATTACHED state
        await user.fetch()  # Explicitly fetch data
        print(user.name)  # Now can access attributes

        # Update and save
        user.year = 1816
        await user.save()

        # Delete
        await user.delete()
    """

    def __getattr__(self, name: str) -> Any:
        """
        Handle attribute access for document fields.

        Note: Unlike sync version, this does NOT support lazy loading.
        Users must explicitly fetch() before accessing attributes.

        Args:
            name: The attribute name being accessed.

        Returns:
            The value of the field from the internal _data cache.

        Raises:
            AttributeError: If accessing attributes on ATTACHED (not fetched),
                           or if attribute doesn't exist.
        """
        if name in self._INTERNAL_ATTRS:
            raise AttributeError(f"Internal attribute {name} not set")

        # ATTACHED: Must fetch first (no lazy loading in async)
        if self._state == State.ATTACHED:
            raise AttributeError(
                f"Cannot access attribute '{name}' on ATTACHED AsyncFireObject. "
                f"Call await fetch() first to load data from Firestore."
            )

        # Check if attribute exists in _data
        if name not in self._data:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        return self._data[name]

    # =========================================================================
    # Async Lifecycle Methods
    # =========================================================================

    async def fetch(self, force: bool = False) -> 'AsyncFireObject':
        """
        Fetch document data from Firestore asynchronously.

        Args:
            force: If True, fetch data even if already LOADED.

        Returns:
            Self, to allow method chaining.

        Raises:
            ValueError: If called on DETACHED object.
            RuntimeError: If called on DELETED object.
            NotFound: If document doesn't exist.

        State Transitions:
            ATTACHED -> LOADED
            LOADED -> LOADED (if force=True)

        Example:
            user = db.doc('users/alovelace')  # ATTACHED
            await user.fetch()  # Now LOADED
            await user.fetch(force=True)  # Refresh data
        """
        self._validate_not_detached("fetch()")
        self._validate_not_deleted("fetch()")

        # Skip if already LOADED and not forcing
        if self._state == State.LOADED and not force:
            return self

        # Async fetch from Firestore
        snapshot = await self._doc_ref.get()

        if not snapshot.exists:
            raise NotFound(f"Document {self._doc_ref.path} does not exist")

        # Transition to LOADED with data
        self._transition_to_loaded(snapshot.to_dict() or {})

        return self

    async def save(self, doc_id: Optional[str] = None) -> 'AsyncFireObject':
        """
        Save the object's data to Firestore asynchronously.

        Args:
            doc_id: Optional custom document ID for DETACHED objects.

        Returns:
            Self, to allow method chaining.

        Raises:
            RuntimeError: If called on DELETED object.
            ValueError: If DETACHED without parent_collection.

        State Transitions:
            DETACHED -> LOADED (creates new document)
            LOADED -> LOADED (updates if dirty)

        Example:
            user = collection.new()
            user.name = 'Ada'
            await user.save(doc_id='alovelace')
        """
        self._validate_not_deleted("save()")

        # DETACHED: Create new document
        if self._state == State.DETACHED:
            if not self._parent_collection:
                raise ValueError("DETACHED object has no parent collection")

            collection_ref = self._parent_collection._collection_ref

            # Create document reference
            if doc_id:
                doc_ref = collection_ref.document(doc_id)
            else:
                doc_ref = collection_ref.document()

            # Async save
            await doc_ref.set(self._data)

            # Update state
            object.__setattr__(self, '_doc_ref', doc_ref)
            self._transition_to_loaded(self._data)

            return self

        # ATTACHED/LOADED: Update if dirty
        if self._dirty:
            await self._doc_ref.set(self._data)
            self._mark_clean()

        if self._state == State.ATTACHED:
            object.__setattr__(self, '_state', State.LOADED)

        return self

    async def delete(self) -> None:
        """
        Delete the document from Firestore asynchronously.

        Raises:
            ValueError: If called on DETACHED object.
            RuntimeError: If called on DELETED object.

        State Transitions:
            ATTACHED -> DELETED
            LOADED -> DELETED

        Example:
            user = db.doc('users/alovelace')
            await user.delete()
        """
        self._validate_not_detached("delete()")
        self._validate_not_deleted("delete()")

        # Async delete
        await self._doc_ref.delete()

        # Transition to DELETED
        self._transition_to_deleted()

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    def from_snapshot(
        cls,
        snapshot: DocumentSnapshot,
        parent_collection: Optional[Any] = None
    ) -> 'AsyncFireObject':
        """
        Create an AsyncFireObject from a DocumentSnapshot.

        Args:
            snapshot: DocumentSnapshot from native async API.
            parent_collection: Optional parent collection reference.

        Returns:
            AsyncFireObject in LOADED state.

        Raises:
            ValueError: If snapshot doesn't exist.

        Example:
            async for doc in query.stream():
                user = AsyncFireObject.from_snapshot(doc)
        """
        init_data = cls._create_from_snapshot_base(snapshot, parent_collection)

        obj = cls(
            doc_ref=init_data['doc_ref'],
            initial_state=init_data['initial_state'],
            parent_collection=init_data['parent_collection']
        )

        object.__setattr__(obj, '_data', init_data['data'])
        object.__setattr__(obj, '_dirty', False)

        return obj
