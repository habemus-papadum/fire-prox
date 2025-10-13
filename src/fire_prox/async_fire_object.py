"""Asynchronous document proxy with optional schema typing."""

from __future__ import annotations

from typing import Any, Dict, Generic, Optional, TypeVar

from google.cloud.exceptions import NotFound
from google.cloud.firestore_v1.async_document import AsyncDocumentReference
from google.cloud.firestore_v1.document import DocumentSnapshot

from .base_fire_object import BaseFireObject
from .state import State

SchemaT = TypeVar("SchemaT")


class AsyncFireObject(BaseFireObject[SchemaT], Generic[SchemaT]):
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

    # =========================================================================
    # Firestore I/O Hooks
    # =========================================================================

    async def _get_snapshot(self, transaction: Optional[Any] = None) -> DocumentSnapshot:
        """Retrieve a document snapshot using the async client."""
        if transaction is not None:
            return await self._doc_ref.get(transaction=transaction)
        return await self._doc_ref.get()

    def _create_document(self, doc_id: Optional[str] = None) -> AsyncDocumentReference:
        """Create a new async document reference for DETACHED saves."""
        if not self._parent_collection:
            raise ValueError("DETACHED object has no parent collection")

        collection_ref = self._parent_collection._collection_ref
        if doc_id:
            doc_ref = collection_ref.document(doc_id)
        else:
            doc_ref = collection_ref.document()

        object.__setattr__(self, '_doc_ref', doc_ref)

        if self._sync_client is not None:
            sync_ref = self._sync_client.document(doc_ref.path)
            object.__setattr__(self, '_sync_doc_ref', sync_ref)

        return doc_ref

    async def _write_set(
        self,
        data: Dict[str, Any],
        doc_ref: Optional[AsyncDocumentReference] = None,
        transaction: Optional[Any] = None,
        batch: Optional[Any] = None,
    ) -> None:
        """Persist data via a set call on the async client."""
        target_ref = doc_ref or self._doc_ref

        if transaction is not None:
            transaction.set(target_ref, data)
        elif batch is not None:
            batch.set(target_ref, data)
        else:
            await target_ref.set(data)

    async def _write_update(
        self,
        update_dict: Dict[str, Any],
        transaction: Optional[Any] = None,
        batch: Optional[Any] = None,
    ) -> None:
        """Perform an update operation using the async client."""
        if transaction is not None:
            transaction.update(self._doc_ref, update_dict)
        elif batch is not None:
            batch.update(self._doc_ref, update_dict)
        else:
            await self._doc_ref.update(update_dict)

    async def _write_delete(self, batch: Optional[Any] = None) -> None:
        """Delete the document using the async client."""
        if batch is not None:
            batch.delete(self._doc_ref)
        else:
            await self._doc_ref.delete()

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

            # Get data and convert special types (DocumentReference → FireObject, etc.)
            data = snapshot.to_dict() or {}
            converted_data = {}
            sync_client = (
                self._sync_doc_ref._client
                if hasattr(self, '_sync_doc_ref') and self._sync_doc_ref
                else None
            )
            for key, value in data.items():
                converted_data[key] = self._convert_snapshot_value_for_retrieval(
                    value,
                    is_async=True,
                    sync_client=sync_client,
                )

            # Transition to LOADED with converted data
            self._transition_to_loaded(converted_data)

        return self._materialize_field(name)

    # =========================================================================
    # Async Lifecycle Methods
    # =========================================================================

    async def fetch(self, force: bool = False, transaction: Optional[Any] = None) -> 'AsyncFireObject[SchemaT]':
        """
        Fetch document data from Firestore asynchronously.

        Args:
            force: If True, fetch data even if already LOADED.
            transaction: Optional transaction object for transactional reads.

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
            # Normal fetch
            user = db.doc('users/alovelace')  # ATTACHED
            await user.fetch()  # Now LOADED

            # Transactional fetch
            transaction = db.transaction()
            @firestore.async_transactional
            async def read_user(transaction):
                await user.fetch(transaction=transaction)
                return user.credits
            credits = await read_user(transaction)
        """
        if self._should_skip_fetch(force):
            return self

        snapshot = await self._get_snapshot(transaction)
        self._process_snapshot(snapshot, is_async=True)

        return self

    async def save(
        self,
        doc_id: Optional[str] = None,
        transaction: Optional[Any] = None,
        batch: Optional[Any] = None,
    ) -> 'AsyncFireObject[SchemaT]':
        """
        Save the object's data to Firestore asynchronously.

        Args:
            doc_id: Optional custom document ID for DETACHED objects.
            transaction: Optional transaction object for transactional writes.
            batch: Optional batch object for batched writes. If provided,
                  the write will be accumulated in the batch (committed later).

        Returns:
            Self, to allow method chaining.

        Raises:
            RuntimeError: If called on DELETED object.
            ValueError: If DETACHED without parent_collection, or if
                       trying to create a new document within a transaction or batch.

        State Transitions:
            DETACHED -> LOADED (creates new document)
            LOADED -> LOADED (updates if dirty)

        Example:
            # Normal save
            user = collection.new()
            user.name = 'Ada'
            await user.save(doc_id='alovelace')

            # Transactional save
            transaction = db.transaction()
            @firestore.async_transactional
            async def update_user(transaction):
                await user.fetch(transaction=transaction)
                user.credits += 10
                await user.save(transaction=transaction)
            await update_user(transaction)

            # Batch save
            batch = db.batch()
            user1.save(batch=batch)
            user2.save(batch=batch)
            await batch.commit()  # Commit all operations
        """
        self._validate_not_deleted("save()")

        if self._state == State.DETACHED:
            doc_ref, storage_data = self._prepare_detached_save(doc_id, transaction, batch)
            await self._write_set(storage_data, doc_ref=doc_ref)
            object.__setattr__(self, '_state', State.LOADED)
            self._mark_clean()
            return self

        if self._state == State.LOADED:
            if not self.is_dirty():
                return self

            update_dict = self._build_update_dict()
            await self._write_update(update_dict, transaction=transaction, batch=batch)
            self._mark_clean()
            return self

        if self._state == State.ATTACHED:
            storage_data = self._prepare_data_for_storage()
            await self._write_set(storage_data, transaction=transaction, batch=batch)
            object.__setattr__(self, '_state', State.LOADED)
            self._mark_clean()
            return self

        return self

    async def delete(self, batch: Optional[Any] = None) -> None:
        """
        Delete the document from Firestore asynchronously.

        Args:
            batch: Optional batch object for batched deletes. If provided,
                  the delete will be accumulated in the batch (committed later).

        Raises:
            ValueError: If called on DETACHED object.
            RuntimeError: If called on DELETED object.

        State Transitions:
            ATTACHED -> DELETED
            LOADED -> DELETED

        Example:
            user = db.doc('users/alovelace')
            await user.delete()

            # Batch delete
            batch = db.batch()
            user1.delete(batch=batch)
            user2.delete(batch=batch)
            await batch.commit()  # Commit all operations
        """
        self._prepare_delete()
        await self._write_delete(batch=batch)
        self._transition_to_deleted()

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    def from_snapshot(
        cls: type['AsyncFireObject[Any]'],
        snapshot: DocumentSnapshot,
        parent_collection: Optional[Any] = None,
        sync_client: Optional[Any] = None
    ) -> 'AsyncFireObject[Any]':
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
            sync_client=sync_client,
            schema_type=init_data.get('schema_type'),
            schema_metadata=init_data.get('schema_metadata'),
        )

        object.__setattr__(obj, '_data', init_data['data'])
        # Dirty tracking is already cleared by __init__ and _transition_to_loaded

        return obj
