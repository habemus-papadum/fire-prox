"""
FireObject: The core proxy class for Firestore documents (synchronous).

This module implements the synchronous FireObject class, which serves as a
schemaless, state-aware proxy for Firestore documents.
"""

from typing import Any, Dict, Optional

from google.cloud.firestore_v1.document import DocumentReference, DocumentSnapshot

from .base_fire_object import BaseFireObject
from .state import State


class FireObject(BaseFireObject):
    """
    A schemaless, state-aware proxy for a Firestore document (synchronous).

    FireObject provides an object-oriented interface to Firestore documents,
    allowing attribute-style access to document fields and automatic state
    management throughout the document's lifecycle.

    The object maintains an internal state machine (DETACHED -> ATTACHED ->
    LOADED -> DELETED) and tracks modifications to enable efficient partial
    updates.

    This is the synchronous implementation that supports lazy loading via
    automatic fetch on attribute access.

    Usage Examples:
        # Create a new document (DETACHED state)
        user = collection.new()
        user.name = 'Ada Lovelace'
        user.year = 1815
        user.save()  # Transitions to LOADED

        # Load existing document (ATTACHED -> LOADED on access)
        user = db.doc('users/alovelace')  # ATTACHED state
        print(user.name)  # Triggers fetch, transitions to LOADED

        # Update and save
        user.year = 1816  # Marks as dirty
        user.save()  # Performs update

        # Delete
        user.delete()  # Transitions to DELETED
    """

    # =========================================================================
    # Dynamic Attribute Handling (Sync-specific for lazy loading)
    # =========================================================================

    def __getattr__(self, name: str) -> Any:
        """Handle attribute access for document fields with lazy loading."""

        if name == '_data':
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        if self._state == State.ATTACHED:
            self.fetch()

        return self._materialize_field(name)

    # =========================================================================
    # Core Lifecycle Methods (Sync-specific I/O)
    # =========================================================================

    def fetch(self, force: bool = False, transaction: Optional[Any] = None) -> 'FireObject':
        """
        Fetch document data from Firestore (synchronous).

        Retrieves the latest data from Firestore and populates the internal
        _data cache. This method transitions ATTACHED objects to LOADED state
        and can refresh data for already-LOADED objects.

        Args:
            force: If True, fetch data even if already LOADED. Useful for
                  refreshing data to get latest changes from Firestore.
                  Default is False.
            transaction: Optional transaction object for transactional reads.
                        If provided, the read will be part of the transaction.

        Returns:
            Self, to allow method chaining.

        Raises:
            ValueError: If called on a DETACHED object (no DocumentReference).
            RuntimeError: If called on a DELETED object.
            NotFound: If document doesn't exist in Firestore.

        State Transitions:
            ATTACHED -> LOADED: First fetch populates data
            LOADED -> LOADED: Refreshes data if force=True

        Example:
            # Normal fetch
            user = db.doc('users/alovelace')  # ATTACHED
            user.fetch()  # Now LOADED with data

            # Transactional fetch
            transaction = db.transaction()
            @firestore.transactional
            def read_user(transaction):
                user.fetch(transaction=transaction)
                return user.credits
            credits = read_user(transaction)
        """
        if self._should_skip_fetch(force):
            return self

        snapshot = self._get_snapshot(transaction=transaction)
        return self._finalize_fetch_from_snapshot(snapshot)

    def save(
        self,
        doc_id: Optional[str] = None,
        transaction: Optional[Any] = None,
        batch: Optional[Any] = None,
    ) -> 'FireObject':
        """
        Save the object's data to Firestore (synchronous).

        Creates or updates the Firestore document based on the object's
        current state. For DETACHED objects, creates a new document. For
        LOADED objects, performs a full overwrite (Phase 1).

        Args:
            doc_id: Optional custom document ID. Only used when saving a
                   DETACHED object. If None, Firestore auto-generates an ID.
            transaction: Optional transaction object for transactional writes.
                        If provided, the write will be part of the transaction.
            batch: Optional batch object for batched writes. If provided,
                  the write will be accumulated in the batch (committed later).

        Returns:
            Self, to allow method chaining.

        Raises:
            RuntimeError: If called on a DELETED object.
            ValueError: If DETACHED object has no parent collection, or if
                       trying to create a new document within a transaction or batch.

        State Transitions:
            DETACHED -> LOADED: Creates new document with doc_id or auto-ID
            LOADED -> LOADED: Updates document if dirty, no-op if clean

        Example:
            # Create new document
            user = collection.new()
            user.name = 'Ada'
            user.save(doc_id='alovelace')  # DETACHED -> LOADED

            # Update existing
            user.year = 1816
            user.save()  # Performs update

            # Transactional save
            transaction = db.transaction()
            @firestore.transactional
            def update_user(transaction):
                user.fetch(transaction=transaction)
                user.credits += 10
                user.save(transaction=transaction)
            update_user(transaction)

            # Batch save
            batch = db.batch()
            user1.save(batch=batch)
            user2.save(batch=batch)
            batch.commit()  # Commit all operations
        """
        plan = self._build_save_plan(doc_id, transaction, batch)
        self._execute_save_plan_sync(plan, transaction, batch)
        return self

    def delete(self, batch: Optional[Any] = None) -> None:
        """
        Delete the document from Firestore (synchronous).

        Removes the document from Firestore and transitions the object to
        DELETED state. After deletion, the object retains its ID and path
        for reference but cannot be modified or saved.

        Args:
            batch: Optional batch object for batched deletes. If provided,
                  the delete will be accumulated in the batch (committed later).

        Raises:
            ValueError: If called on a DETACHED object (no document to delete).
            RuntimeError: If called on an already-DELETED object.

        State Transitions:
            ATTACHED -> DELETED: Deletes document (data never loaded)
            LOADED -> DELETED: Deletes document (data was loaded)

        Example:
            user = db.doc('users/alovelace')
            user.delete()  # Document removed from Firestore
            print(user.state)  # State.DELETED
            print(user.id)  # Still accessible: 'alovelace'

            # Batch delete
            batch = db.batch()
            user1.delete(batch=batch)
            user2.delete(batch=batch)
            batch.commit()  # Commit all operations
        """
        self._delete_sync(batch=batch)

    # =========================================================================
    # Factory Methods
    # =========================================================================

    # ---------------------------------------------------------------------
    # BaseFireObject hook implementations
    # ---------------------------------------------------------------------

    def _get_snapshot(self, transaction: Optional[Any] = None) -> DocumentSnapshot:
        if transaction is not None:
            return self._doc_ref.get(transaction=transaction)
        return self._doc_ref.get()

    def _create_document(self, doc_id: Optional[str] = None) -> DocumentReference:
        if not self._parent_collection:
            raise ValueError("DETACHED object has no parent collection")

        collection_ref = self._parent_collection._collection_ref
        if doc_id:
            return collection_ref.document(doc_id)
        return collection_ref.document()

    def _write_set(
        self,
        doc_ref: DocumentReference,
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
        doc_ref.set(data)

    def _write_update(
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
        self._doc_ref.update(update_dict)

    def _write_delete(self, batch: Optional[Any] = None) -> None:
        if batch is not None:
            batch.delete(self._doc_ref)
            return
        self._doc_ref.delete()

    @classmethod
    def from_snapshot(
        cls,
        snapshot: DocumentSnapshot,
        parent_collection: Optional[Any] = None
    ) -> 'FireObject':
        """
        Create a FireObject from a Firestore DocumentSnapshot.

        This factory method is the primary "hydration" mechanism for
        converting native Firestore query results into FireObject instances.
        It creates an object in LOADED state with data already populated.

        Args:
            snapshot: A DocumentSnapshot from google-cloud-firestore, typically
                     obtained from query results or document.get().
            parent_collection: Optional reference to parent FireCollection.

        Returns:
            A new FireObject instance in LOADED state with data from snapshot.

        Raises:
            ValueError: If snapshot doesn't exist (snapshot.exists is False).

        Example:
            # Hydrate from native query
            native_query = client.collection('users').where('year', '>', 1800)
            results = [FireObject.from_snapshot(snap)
                      for snap in native_query.stream()]

            # Hydrate from direct get
            snap = client.document('users/alovelace').get()
            user = FireObject.from_snapshot(snap)
        """
        # Use base class helper to extract snapshot data
        init_params = cls._create_from_snapshot_base(snapshot, parent_collection)

        # Create FireObject in LOADED state
        obj = cls(
            doc_ref=init_params['doc_ref'],
            initial_state=init_params['initial_state'],
            parent_collection=init_params['parent_collection']
        )

        # Populate data from snapshot
        object.__setattr__(obj, '_data', init_params['data'])

        return obj
