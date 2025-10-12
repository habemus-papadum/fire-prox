"""
AsyncFireObject: Async version of FireObject for AsyncClient.

This module implements the asynchronous FireObject class for use with
google.cloud.firestore.AsyncClient.
"""

from typing import Any, Optional

from google.cloud import firestore
from google.cloud.exceptions import NotFound
from google.cloud.firestore_v1.async_document import AsyncDocumentReference
from google.cloud.firestore_v1.document import DocumentSnapshot, DocumentReference
from google.cloud.firestore_v1.vector import Vector

from .base_fire_object import BaseFireObject
from .state import State


class AsyncFireObject(BaseFireObject):
    """
    Asynchronous schemaless, state-aware proxy for a Firestore document.

    AsyncFireObject provides an object-oriented interface to Firestore documents
    using the async/await pattern for all I/O operations.

    Lazy Loading: AsyncFireObject supports lazy loading via automatic fetch on
    attribute access. When accessing an attribute on an ATTACHED object, it will
    automatically fetch data from Firestore (using a synchronous thread to run
    the async fetch). This happens once per object - subsequent accesses are
    instant dict lookups.

    Usage Examples:
        # Create a new document (DETACHED state)
        user = collection.new()
        user.name = 'Ada Lovelace'
        user.year = 1815
        await user.save()  # Transitions to LOADED

        # Load existing document with lazy loading (automatic fetch)
        user = db.doc('users/alovelace')  # ATTACHED state
        print(user.name)  # Automatically fetches data, transitions to LOADED

        # Or explicitly fetch if preferred
        user = db.doc('users/alovelace')
        await user.fetch()  # Explicit async fetch
        print(user.name)

        # Update and save
        user.year = 1816
        await user.save()

        # Delete
        await user.delete()
    """

    def __getattr__(self, name: str) -> Any:
        """
        Handle attribute access for document fields with lazy loading.

        This method implements lazy loading: if the object is in ATTACHED state,
        accessing any data attribute will automatically trigger a synchronous fetch
        to load the data from Firestore using a companion sync client.

        This fetch happens **once per object** - after the first attribute access,
        the object transitions to LOADED state and subsequent accesses are instant
        dict lookups.

        Args:
            name: The attribute name being accessed.

        Returns:
            The value of the field from the internal _data cache.

        Raises:
            AttributeError: If the attribute doesn't exist in _data after
                           fetching (if necessary).
            NotFound: If document doesn't exist in Firestore (during lazy load).

        State Transitions:
            ATTACHED -> LOADED: Automatically fetches data on first access.

        Example:
            user = db.doc('users/alovelace')  # ATTACHED
            name = user.name  # Triggers sync fetch, transitions to LOADED
            year = user.year  # No fetch needed, already LOADED
        """
        if name in self._INTERNAL_ATTRS:
            raise AttributeError(f"Internal attribute {name} not set")

        # If we're in ATTACHED state, trigger lazy loading via sync fetch
        if self._state == State.ATTACHED and self._sync_doc_ref:
            # Use sync doc ref for lazy loading (synchronous fetch)
            snapshot = self._sync_doc_ref.get()

            if not snapshot.exists:
                raise NotFound(f"Document {self._sync_doc_ref.path} does not exist")

            # Get data and convert special types (DocumentReference → FireObject, Vector → FireVector, etc.)
            data = snapshot.to_dict() or {}
            converted_data = {}
            sync_client = self._sync_doc_ref._client if hasattr(self, '_sync_doc_ref') and self._sync_doc_ref else None
            for key, value in data.items():
                converted_data[key] = self._convert_snapshot_value_for_retrieval(value, is_async=True, sync_client=sync_client)

            # Transition to LOADED with converted data
            self._transition_to_loaded(converted_data)

        # Check if attribute exists in _data (now in LOADED state)
        if name not in self._data:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        value = self._data[name]

        # Convert native Vector to FireVector on retrieval
        if isinstance(value, Vector):
            from .fire_vector import FireVector
            fire_vec = FireVector.from_firestore_vector(value)
            # Cache the converted object
            self._data[name] = fire_vec
            return fire_vec

        # Convert DocumentReference to AsyncFireObject on retrieval
        if isinstance(value, (DocumentReference, AsyncDocumentReference)):
            # Return async version with sync_doc_ref for lazy loading
            sync_ref = None
            if isinstance(value, DocumentReference):
                sync_ref = value
            elif isinstance(value, AsyncDocumentReference) and hasattr(self, '_sync_doc_ref') and self._sync_doc_ref:
                # Create sync ref from async ref using sync_client
                sync_client = self._sync_doc_ref._client
                sync_ref = sync_client.document(value.path)

            async_obj = AsyncFireObject(
                doc_ref=value,
                initial_state=State.ATTACHED,
                sync_doc_ref=sync_ref,
                sync_client=self._sync_doc_ref._client if hasattr(self, '_sync_doc_ref') and self._sync_doc_ref else None
            )
            # Cache the converted object so subsequent accesses return the same instance
            self._data[name] = async_obj
            return async_obj

        return value

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

        # Get data and convert special types (DocumentReference → FireObject, Vector → FireVector, etc.)
        data = snapshot.to_dict() or {}
        converted_data = {}
        sync_client = self._sync_doc_ref._client if hasattr(self, '_sync_doc_ref') and self._sync_doc_ref else None
        for key, value in data.items():
            converted_data[key] = self._convert_snapshot_value_for_retrieval(value, is_async=True, sync_client=sync_client)

        # Transition to LOADED with converted data
        self._transition_to_loaded(converted_data)

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

            # Prepare data for storage (convert FireObjects back to DocumentReferences)
            storage_data = self._prepare_data_for_storage()

            # Async save
            await doc_ref.set(storage_data)

            # Update state
            object.__setattr__(self, '_doc_ref', doc_ref)
            self._transition_to_loaded(self._data)

            return self

        # ATTACHED/LOADED: Update if dirty
        if self.is_dirty():
            # Phase 2: Perform efficient partial update for LOADED state
            if self._state == State.LOADED:
                # Build update dict with modified and deleted fields
                update_dict = {}

                # Add modified fields (convert to storage format)
                for field in self._dirty_fields:
                    update_dict[field] = self._convert_value_for_storage(self._data[field])

                # Add deleted fields with DELETE_FIELD sentinel
                for field in self._deleted_fields:
                    update_dict[field] = firestore.DELETE_FIELD

                # Add atomic operations (ArrayUnion, ArrayRemove, Increment)
                for field, operation in self._atomic_ops.items():
                    update_dict[field] = operation

                # Perform partial update
                await self._doc_ref.update(update_dict)
            else:
                # ATTACHED state: use .set() for full overwrite
                # Prepare data for storage (convert FireObjects back to DocumentReferences)
                storage_data = self._prepare_data_for_storage()
                await self._doc_ref.set(storage_data)

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
        parent_collection: Optional[Any] = None,
        sync_client: Optional[Any] = None
    ) -> 'AsyncFireObject':
        """
        Create an AsyncFireObject from a DocumentSnapshot.

        Args:
            snapshot: DocumentSnapshot from native async API.
            parent_collection: Optional parent collection reference.
            sync_client: Optional sync Firestore client for async lazy loading.

        Returns:
            AsyncFireObject in LOADED state.

        Raises:
            ValueError: If snapshot doesn't exist.

        Example:
            async for doc in query.stream():
                user = AsyncFireObject.from_snapshot(doc)
        """
        init_data = cls._create_from_snapshot_base(snapshot, parent_collection, sync_client)

        obj = cls(
            doc_ref=init_data['doc_ref'],
            initial_state=init_data['initial_state'],
            parent_collection=init_data['parent_collection'],
            sync_client=sync_client
        )

        object.__setattr__(obj, '_data', init_data['data'])
        # Dirty tracking is already cleared by __init__ and _transition_to_loaded

        return obj
