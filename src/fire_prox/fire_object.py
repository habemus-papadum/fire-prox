"""
FireObject: The core proxy class for Firestore documents (synchronous).

This module implements the synchronous FireObject class, which serves as a
schemaless, state-aware proxy for Firestore documents.
"""

from typing import Any, Optional
from google.cloud.firestore_v1.document import DocumentSnapshot
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
            return self._data[name]

        # Attribute not found
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    # =========================================================================
    # Core Lifecycle Methods (Sync-specific I/O)
    # =========================================================================

    def fetch(self, force: bool = False) -> 'FireObject':
        """
        Fetch document data from Firestore (synchronous).

        Retrieves the latest data from Firestore and populates the internal
        _data cache. This method transitions ATTACHED objects to LOADED state
        and can refresh data for already-LOADED objects.

        Args:
            force: If True, fetch data even if already LOADED. Useful for
                  refreshing data to get latest changes from Firestore.
                  Default is False.

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
            user = db.doc('users/alovelace')  # ATTACHED
            user.fetch()  # Now LOADED with data
            # ... make external changes in Firestore ...
            user.fetch(force=True)  # Refresh data
        """
        # Validate state
        self._validate_not_detached("fetch()")
        self._validate_not_deleted("fetch()")

        # Skip fetch if already LOADED and not forcing
        if self._state == State.LOADED and not force:
            return self

        # Fetch from Firestore (synchronous)
        snapshot = self._doc_ref.get()

        if not snapshot.exists:
            raise NotFound(f"Document {self._doc_ref.path} does not exist")

        # Transition to LOADED state with data
        self._transition_to_loaded(snapshot.to_dict() or {})

        return self

    def save(self, doc_id: Optional[str] = None) -> 'FireObject':
        """
        Save the object's data to Firestore (synchronous).

        Creates or updates the Firestore document based on the object's
        current state. For DETACHED objects, creates a new document. For
        LOADED objects, performs a full overwrite (Phase 1).

        Args:
            doc_id: Optional custom document ID. Only used when saving a
                   DETACHED object. If None, Firestore auto-generates an ID.

        Returns:
            Self, to allow method chaining.

        Raises:
            RuntimeError: If called on a DELETED object.
            ValueError: If DETACHED object has no parent collection.

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
        """
        # Check if we're trying to save a DELETED object
        self._validate_not_deleted("save()")

        # Handle DETACHED state - create new document
        if self._state == State.DETACHED:
            if not self._parent_collection:
                raise ValueError("DETACHED object has no parent collection")

            # Get the collection reference
            collection_ref = self._parent_collection._collection_ref

            # Create document reference (with custom ID or auto-generated)
            if doc_id:
                doc_ref = collection_ref.document(doc_id)
            else:
                doc_ref = collection_ref.document()

            # Save data to Firestore
            doc_ref.set(self._data)

            # Update internal state
            object.__setattr__(self, '_doc_ref', doc_ref)
            object.__setattr__(self, '_state', State.LOADED)
            self._mark_clean()

            return self

        # Handle LOADED state - update if dirty
        if self._state == State.LOADED:
            # Skip if not dirty
            if not self._dirty:
                return self

            # Perform full overwrite (Phase 1)
            self._doc_ref.set(self._data)

            # Clear dirty flag
            self._mark_clean()

            return self

        # Handle ATTACHED state - set data
        if self._state == State.ATTACHED:
            # For ATTACHED, we can just do a set operation
            self._doc_ref.set(self._data)
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
