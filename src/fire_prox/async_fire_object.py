"""
AsyncFireObject: Async version of FireObject for AsyncClient.

This module implements the asynchronous FireObject class for use with
google.cloud.firestore.AsyncClient.
"""

from typing import Any, Dict, Optional

from google.cloud.firestore_v1.async_document import AsyncDocumentReference
from google.cloud.firestore_v1.document import DocumentSnapshot

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
        """Handle attribute access with synchronous lazy loading support."""

        if name in self._INTERNAL_ATTRS:
            raise AttributeError(f"Internal attribute {name} not set")

        if self._state == State.ATTACHED and self._sync_doc_ref:
            snapshot = self._sync_doc_ref.get()
            self._finalize_fetch_from_snapshot(snapshot)

        return self._materialize_field(name)

    # =========================================================================
    # Async Lifecycle Methods
    # =========================================================================

    async def fetch(self, force: bool = False, transaction: Optional[Any] = None) -> 'AsyncFireObject':
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

        snapshot = await self._get_snapshot(transaction=transaction)
        return self._finalize_fetch_from_snapshot(snapshot)

    async def save(
        self,
        doc_id: Optional[str] = None,
        transaction: Optional[Any] = None,
        batch: Optional[Any] = None,
    ) -> 'AsyncFireObject':
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
        plan = self._build_save_plan(doc_id, transaction, batch)
        await self._execute_save_plan_async(plan, transaction, batch)

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
        await self._delete_async(batch=batch)

    # =========================================================================
    # Factory Methods
    # =========================================================================

    # ---------------------------------------------------------------------
    # BaseFireObject hook implementations
    # ---------------------------------------------------------------------

    async def _get_snapshot(self, transaction: Optional[Any] = None) -> DocumentSnapshot:
        if transaction is not None:
            return await self._doc_ref.get(transaction=transaction)
        return await self._doc_ref.get()

    def _create_document(self, doc_id: Optional[str] = None) -> AsyncDocumentReference:
        if not self._parent_collection:
            raise ValueError("DETACHED object has no parent collection")

        collection_ref = self._parent_collection._collection_ref
        if doc_id:
            return collection_ref.document(doc_id)
        return collection_ref.document()

    async def _write_set(
        self,
        doc_ref: AsyncDocumentReference,
        data: Dict[str, Any],
        transaction: Optional[Any] = None,
        batch: Optional[Any] = None,
    ) -> None:
        if transaction is not None:
            transaction.set(doc_ref, data)
            return
        if batch is not None:
            batch.set(doc_ref, data)
            return
        await doc_ref.set(data)

    async def _write_update(
        self,
        update_dict: Dict[str, Any],
        transaction: Optional[Any] = None,
        batch: Optional[Any] = None,
    ) -> None:
        if transaction is not None:
            transaction.update(self._doc_ref, update_dict)
            return
        if batch is not None:
            batch.update(self._doc_ref, update_dict)
            return
        await self._doc_ref.update(update_dict)

    async def _write_delete(self, batch: Optional[Any] = None) -> None:
        if batch is not None:
            batch.delete(self._doc_ref)
            return
        await self._doc_ref.delete()

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
