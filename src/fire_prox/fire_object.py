"""
FireObject: The core proxy class for Firestore documents (synchronous).

This module implements the synchronous FireObject class, which serves as a
schemaless, state-aware proxy for Firestore documents.
"""

from typing import Any, Optional
from google.cloud import firestore
from google.cloud.firestore_v1.document import DocumentSnapshot, DocumentReference
from google.cloud.firestore_v1.vector import Vector
from google.cloud.exceptions import NotFound
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

        # Check if attribute exists in _data
        if name in self._data:
            value = self._data[name]

            # Convert native Vector to FireVector on retrieval
            if isinstance(value, Vector):
                from .fire_vector import FireVector
                fire_vec = FireVector.from_firestore_vector(value)
                # Cache the converted object
                self._data[name] = fire_vec
                return fire_vec

            # Convert DocumentReference to FireObject on retrieval
            if isinstance(value, DocumentReference):
                fire_obj = FireObject(doc_ref=value, initial_state=State.ATTACHED)
                # Cache the converted object so subsequent accesses return the same instance
                self._data[name] = fire_obj
                return fire_obj

            # Recursively convert lists containing references
            if isinstance(value, list):
                converted_list = [
                    FireObject(doc_ref=item, initial_state=State.ATTACHED)
                    if isinstance(item, DocumentReference)
                    else item
                    for item in value
                ]
                # Cache if any conversions were made
                if any(isinstance(item, DocumentReference) for item in value):
                    self._data[name] = converted_list
                return converted_list

            # Recursively convert dicts containing references
            if isinstance(value, dict):
                converted_dict = {
                    k: (
                        FireObject(doc_ref=v, initial_state=State.ATTACHED)
                        if isinstance(v, DocumentReference)
                        else v
                    )
                    for k, v in value.items()
                }
                # Cache if any conversions were made
                if any(isinstance(v, DocumentReference) for v in value.values()):
                    self._data[name] = converted_dict
                return converted_dict

            return value

        # Attribute not found
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

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
        # Validate state
        self._validate_not_detached("fetch()")
        self._validate_not_deleted("fetch()")

        # Skip fetch if already LOADED and not forcing
        if self._state == State.LOADED and not force:
            return self

        # Fetch from Firestore (synchronous)
        # Use transaction if provided, otherwise normal get
        if transaction is not None:
            snapshot = self._doc_ref.get(transaction=transaction)
        else:
            snapshot = self._doc_ref.get()

        if not snapshot.exists:
            raise NotFound(f"Document {self._doc_ref.path} does not exist")

        # Get data and convert special types (DocumentReference → FireObject, Vector → FireVector, etc.)
        data = snapshot.to_dict() or {}
        converted_data = {}
        for key, value in data.items():
            converted_data[key] = self._convert_snapshot_value_for_retrieval(value, is_async=False)

        # Transition to LOADED state with converted data
        self._transition_to_loaded(converted_data)

        return self

    def save(self, doc_id: Optional[str] = None, transaction: Optional[Any] = None) -> 'FireObject':
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

        Returns:
            Self, to allow method chaining.

        Raises:
            RuntimeError: If called on a DELETED object.
            ValueError: If DETACHED object has no parent collection, or if
                       trying to create a new document within a transaction.

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
        """
        # Check if we're trying to save a DELETED object
        self._validate_not_deleted("save()")

        # Handle DETACHED state - create new document
        if self._state == State.DETACHED:
            if transaction is not None:
                raise ValueError(
                    "Cannot create new documents (DETACHED -> LOADED) within a transaction. "
                    "Create the document first, then use transactions for updates."
                )

            if not self._parent_collection:
                raise ValueError("DETACHED object has no parent collection")

            # Get the collection reference
            collection_ref = self._parent_collection._collection_ref

            # Create document reference (with custom ID or auto-generated)
            if doc_id:
                doc_ref = collection_ref.document(doc_id)
            else:
                doc_ref = collection_ref.document()

            # Prepare data for storage (convert FireObjects back to DocumentReferences)
            storage_data = self._prepare_data_for_storage()

            # Save data to Firestore
            doc_ref.set(storage_data)

            # Update internal state
            object.__setattr__(self, '_doc_ref', doc_ref)
            object.__setattr__(self, '_state', State.LOADED)
            self._mark_clean()

            return self

        # Handle LOADED state - update if dirty
        if self._state == State.LOADED:
            # Skip if not dirty
            if not self.is_dirty():
                return self

            # Phase 2: Perform efficient partial update
            # Build update dict with modified fields
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

            # Perform partial update with or without transaction
            if transaction is not None:
                transaction.update(self._doc_ref, update_dict)
            else:
                self._doc_ref.update(update_dict)

            # Clear dirty tracking
            self._mark_clean()

            return self

        # Handle ATTACHED state - set data
        if self._state == State.ATTACHED:
            # Prepare data for storage (convert FireObjects back to DocumentReferences)
            storage_data = self._prepare_data_for_storage()
            # For ATTACHED, we can just do a set operation
            if transaction is not None:
                transaction.set(self._doc_ref, storage_data)
            else:
                self._doc_ref.set(storage_data)
            object.__setattr__(self, '_state', State.LOADED)
            self._mark_clean()
            return self

        return self

    def delete(self) -> None:
        """
        Delete the document from Firestore (synchronous).

        Removes the document from Firestore and transitions the object to
        DELETED state. After deletion, the object retains its ID and path
        for reference but cannot be modified or saved.

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
        """
        # Validate state
        self._validate_not_detached("delete()")
        self._validate_not_deleted("delete()")

        # Delete from Firestore (synchronous)
        self._doc_ref.delete()

        # Transition to DELETED state
        self._transition_to_deleted()

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
