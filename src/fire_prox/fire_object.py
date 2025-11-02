"""
FireObject: The core proxy class for Firestore documents (synchronous).

This module implements the synchronous FireObject class, which serves as a
schemaless, state-aware proxy for Firestore documents.
"""

from typing import Any, Dict, List, Optional

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
    # Firestore I/O Hooks
    # =========================================================================

    def _get_snapshot(self, transaction: Optional[Any] = None) -> DocumentSnapshot:
        """Retrieve a document snapshot using the synchronous client."""
        if transaction is not None:
            return self._doc_ref.get(transaction=transaction)
        return self._doc_ref.get()

    def _create_document(self, doc_id: Optional[str] = None) -> DocumentReference:
        """Create a new synchronous document reference for DETACHED saves."""
        if not self._parent_collection:
            raise ValueError("DETACHED object has no parent collection")

        collection_ref = self._parent_collection._collection_ref
        if doc_id:
            doc_ref = collection_ref.document(doc_id)
        else:
            doc_ref = collection_ref.document()

        object.__setattr__(self, '_doc_ref', doc_ref)
        return doc_ref

    def _write_set(
        self,
        data: Dict[str, Any],
        doc_ref: Optional[DocumentReference] = None,
        transaction: Optional[Any] = None,
        batch: Optional[Any] = None,
    ) -> None:
        """Persist data via a set call on the synchronous client."""
        target_ref = doc_ref or self._doc_ref

        if transaction is not None:
            transaction.set(target_ref, data)
        elif batch is not None:
            batch.set(target_ref, data)
        else:
            target_ref.set(data)

    def _write_update(
        self,
        update_dict: Dict[str, Any],
        transaction: Optional[Any] = None,
        batch: Optional[Any] = None,
    ) -> None:
        """Perform an update operation using the synchronous client."""
        if transaction is not None:
            transaction.update(self._doc_ref, update_dict)
        elif batch is not None:
            batch.update(self._doc_ref, update_dict)
        else:
            self._doc_ref.update(update_dict)

    def _write_delete(self, batch: Optional[Any] = None) -> None:
        """Delete the document using the synchronous client."""
        if batch is not None:
            batch.delete(self._doc_ref)
        else:
            self._doc_ref.delete()

    # =========================================================================
    # Dynamic Attribute Handling (Sync-specific for lazy loading)
    # =========================================================================

    def __getattr__(self, name: str) -> Any:
        """
        Handle attribute access for document fields with lazy loading.

        This method implements lazy loading: if the object is in ATTACHED state,
        accessing any data attribute will automatically trigger a fetch() to load
        the data from Firestore.

        Args:
            name: The attribute name being accessed.

        Returns:
            The value of the field from the internal _data cache.

        Raises:
            AttributeError: If the attribute doesn't exist in _data after
                           fetching (if necessary).

        State Transitions:
            ATTACHED -> LOADED: Automatically fetches data on first access.

        Example:
            user = db.doc('users/alovelace')  # ATTACHED
            name = user.name  # Triggers fetch, transitions to LOADED
            year = user.year  # No fetch needed, already LOADED
        """
        # Check if we're accessing internal data
        if name == '_data':
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        # If we're in ATTACHED state, trigger lazy loading
        if self._state == State.ATTACHED:
            # Synchronous fetch for lazy loading
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

        snapshot = self._get_snapshot(transaction)
        self._process_snapshot(snapshot, is_async=False)

        return self

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
        self._validate_not_deleted("save()")

        if self._state == State.DETACHED:
            doc_ref, storage_data = self._prepare_detached_save(doc_id, transaction, batch)
            self._write_set(storage_data, doc_ref=doc_ref)
            object.__setattr__(self, '_state', State.LOADED)
            self._mark_clean()
            return self

        if self._state == State.LOADED:
            if not self.is_dirty():
                return self

            update_dict = self._build_update_dict()
            self._write_update(update_dict, transaction=transaction, batch=batch)
            self._mark_clean()
            return self

        if self._state == State.ATTACHED:
            storage_data = self._prepare_data_for_storage()
            self._write_set(storage_data, transaction=transaction, batch=batch)
            object.__setattr__(self, '_state', State.LOADED)
            self._mark_clean()
            return self

        return self

    def collections(self, names_only: bool = False) -> List[Any]:
        """
        List subcollections beneath this document.

        Args:
            names_only: When True, return collection IDs instead of wrappers.

        Returns:
            List of subcollection names or FireCollection wrappers.
        """
        self._validate_not_detached("collections()")
        self._validate_not_deleted("collections()")

        subcollections = list(self._doc_ref.collections())
        if names_only:
            return [col.id for col in subcollections]

        return [self.collection(col.id) for col in subcollections]

    def delete(
        self,
        batch: Optional[Any] = None,
        *,
        recursive: bool = True,
        batch_size: int = 50,
    ) -> None:
        """
        Delete the document from Firestore (synchronous).

        Removes the document from Firestore and transitions the object to
        DELETED state. After deletion, the object retains its ID and path
        for reference but cannot be modified or saved.

        Args:
            batch: Optional batch object for batched deletes. If provided,
                  the delete will be accumulated in the batch (committed later).
            recursive: When True (default), delete all subcollections first.
            batch_size: Batch size to use for recursive subcollection cleanup.

        Raises:
            ValueError: If called on a DETACHED object (no document to delete).
            RuntimeError: If called on an already-DELETED object.
            ValueError: If recursive deletion is requested while using a batch.

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
            user1.delete(batch=batch, recursive=False)
            user2.delete(batch=batch, recursive=False)
            batch.commit()  # Commit all operations
        """
        if recursive:
            if batch is not None:
                raise ValueError("Cannot delete recursively as part of a batch.")
            if batch_size <= 0:
                raise ValueError(f"batch_size must be positive, got {batch_size}")
            self._delete_descendant_collections(batch_size=batch_size)

        self._prepare_delete()
        self._write_delete(batch=batch)
        self._transition_to_deleted()

    def _delete_descendant_collections(self, batch_size: int) -> None:
        """Delete all subcollections beneath this document."""
        for name in self.collections(names_only=True):
            subcollection = self.collection(name)
            subcollection.delete_all(batch_size=batch_size, recursive=True)

    # =========================================================================
    # Subcollection Utilities
    # =========================================================================

    def delete_subcollection(
        self,
        name: str,
        *,
        batch_size: int = 50,
        recursive: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """
        Delete a subcollection beneath this document.

        Firestore keeps subcollections even after their parent document is
        deleted. This helper clears a specific subcollection using the same
        batched logic as FireCollection.delete_all().

        Args:
            name: Subcollection name relative to this document.
            batch_size: Maximum number of deletes per commit.
            recursive: Whether to delete nested subcollections.
            dry_run: Count affected documents without executing writes.

        Returns:
            Dictionary with counts for deleted documents and subcollections.
        """
        subcollection = self.collection(name)
        return subcollection.delete_all(
            batch_size=batch_size,
            recursive=recursive,
            dry_run=dry_run,
        )

    # =========================================================================
    # Factory Methods
    # =========================================================================

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
