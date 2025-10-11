"""
FireObject: The core proxy class for Firestore documents.

This module implements the FireObject class, which serves as a schemaless,
state-aware proxy for Firestore documents. It provides an intuitive, Pythonic
interface that abstracts away the verbosity of the native Firestore API.
"""

from typing import Any, Optional, Dict
from google.cloud.firestore_v1.document import DocumentReference, DocumentSnapshot
from .state import State


class FireObject:
    """
    A schemaless, state-aware proxy for a Firestore document.

    FireObject provides an object-oriented interface to Firestore documents,
    allowing attribute-style access to document fields and automatic state
    management throughout the document's lifecycle.

    The object maintains an internal state machine (DETACHED -> ATTACHED ->
    LOADED -> DELETED) and tracks modifications to enable efficient partial
    updates.

    Attributes (Internal):
        _doc_ref: The underlying DocumentReference from google-cloud-firestore.
                 None when in DETACHED state.
        _data: Internal dictionary cache of the document's field data.
        _state: Current State enum value (DETACHED, ATTACHED, LOADED, DELETED).
        _dirty: Boolean flag indicating if local data differs from Firestore.
               (Phase 1 uses simple boolean; Phase 2 will use _dirty_fields set)
        _parent_collection: Reference to parent FireCollection if created via .new()

    Usage Examples:
        # Create a new document (DETACHED state)
        user = collection.new()
        user.name = 'Ada Lovelace'
        user.year = 1815
        await user.save()  # Transitions to LOADED

        # Load existing document (ATTACHED -> LOADED on access)
        user = db.doc('users/alovelace')  # ATTACHED state
        print(user.name)  # Triggers fetch, transitions to LOADED

        # Update and save
        user.year = 1816  # Marks as dirty
        await user.save()  # Performs partial update

        # Delete
        await user.delete()  # Transitions to DELETED
    """

    # Class-level constants for internal attribute names to avoid conflicts
    _INTERNAL_ATTRS = {
        '_doc_ref', '_data', '_state', '_dirty', '_parent_collection',
        '_client', '_id', '_path'
    }

    def __init__(
        self,
        doc_ref: Optional[DocumentReference] = None,
        initial_state: State = State.DETACHED,
        parent_collection: Optional[Any] = None,
    ):
        """
        Initialize a FireObject.

        Args:
            doc_ref: Optional DocumentReference from google-cloud-firestore.
                    If provided, initial_state should be ATTACHED.
                    If None, object starts in DETACHED state.
            initial_state: Initial State enum value. Defaults to DETACHED.
            parent_collection: Optional reference to parent FireCollection.
                              Used for auto-generating document IDs on save.

        Note:
            This constructor is primarily used internally. Users typically
            create FireObjects via:
            - db.doc(path) -> ATTACHED state
            - collection.new() -> DETACHED state
            - FireObject.from_snapshot(snapshot) -> LOADED state
        """
        # Use object.__setattr__ to bypass our custom __setattr__
        object.__setattr__(self, '_doc_ref', doc_ref)
        object.__setattr__(self, '_data', {})
        object.__setattr__(self, '_state', initial_state)
        object.__setattr__(self, '_dirty', False)
        object.__setattr__(self, '_parent_collection', parent_collection)

    # =========================================================================
    # State Management and Inspection
    # =========================================================================

    @property
    def state(self) -> State:
        """
        Get the current state of the object.

        Returns:
            Current State enum value (DETACHED, ATTACHED, LOADED, or DELETED).

        Example:
            if user.state == State.LOADED:
                print("Data is loaded")
        """
        raise NotImplementedError("Phase 1 stub")

    def is_detached(self) -> bool:
        """
        Check if object is in DETACHED state.

        Returns:
            True if the object has no Firestore reference and exists only
            in memory. False otherwise.
        """
        raise NotImplementedError("Phase 1 stub")

    def is_attached(self) -> bool:
        """
        Check if object has a Firestore reference.

        Returns:
            True if the object is in ATTACHED, LOADED, or DELETED state
            (i.e., has a DocumentReference). False if DETACHED.
        """
        raise NotImplementedError("Phase 1 stub")

    def is_loaded(self) -> bool:
        """
        Check if object's data has been fetched from Firestore.

        Returns:
            True if the object is in LOADED state with data cached locally.
            False otherwise.
        """
        raise NotImplementedError("Phase 1 stub")

    def is_dirty(self) -> bool:
        """
        Check if object has unsaved local modifications.

        Returns:
            True if any fields have been modified since the last fetch or save.
            False if object is synchronized with Firestore.

        Note:
            DETACHED objects are always considered dirty as all their data
            is new and unsaved.
        """
        raise NotImplementedError("Phase 1 stub")

    def is_deleted(self) -> bool:
        """
        Check if object represents a deleted document.

        Returns:
            True if the object is in DELETED state. False otherwise.

        Note:
            DELETED objects cannot be modified or saved. Attempting to do so
            should raise an appropriate exception.
        """
        raise NotImplementedError("Phase 1 stub")

    @property
    def id(self) -> Optional[str]:
        """
        Get the document ID.

        Returns:
            The document ID if the object has a DocumentReference,
            None if in DETACHED state.

        Example:
            user = db.doc('users/alovelace')
            print(user.id)  # 'alovelace'
        """
        raise NotImplementedError("Phase 1 stub")

    @property
    def path(self) -> Optional[str]:
        """
        Get the full Firestore path of the document.

        Returns:
            The full path (e.g., 'users/alovelace') if the object has a
            DocumentReference, None if in DETACHED state.

        Example:
            user = db.doc('users/alovelace')
            print(user.path)  # 'users/alovelace'
        """
        raise NotImplementedError("Phase 1 stub")

    # =========================================================================
    # Dynamic Attribute Handling (Python Data Model)
    # =========================================================================

    def __getattr__(self, name: str) -> Any:
        """
        Handle attribute access for document fields.

        This method is called when an attribute is not found in the object's
        normal __dict__. It implements lazy loading: if the object is in
        ATTACHED state, accessing any data attribute will automatically
        trigger a fetch() to load the data from Firestore.

        Args:
            name: The attribute name being accessed.

        Returns:
            The value of the field from the internal _data cache.

        Raises:
            AttributeError: If the attribute doesn't exist in _data after
                           fetching (if necessary), or if accessing attributes
                           on a DELETED object.

        State Transitions:
            ATTACHED -> LOADED: Automatically fetches data on first access.

        Example:
            user = db.doc('users/alovelace')  # ATTACHED
            name = user.name  # Triggers fetch, transitions to LOADED
            year = user.year  # No fetch needed, already LOADED
        """
        raise NotImplementedError("Phase 1 stub")

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Handle attribute assignment for document fields.

        This method intercepts all attribute assignments and routes them
        appropriately. Internal attributes (those in _INTERNAL_ATTRS) are
        set normally, while data attributes are stored in the _data cache
        and mark the object as dirty.

        Args:
            name: The attribute name being set.
            value: The value to assign.

        Raises:
            AttributeError: If attempting to modify a DELETED object.

        Side Effects:
            - Updates _data dictionary with the new value
            - Sets _dirty flag to True for data attributes
            - Phase 2 will also add to _dirty_fields set
            - Phase 3 will wrap dicts/lists in ProxiedMap/ProxiedList

        Example:
            user = db.doc('users/alovelace')
            user.name = 'Ada Lovelace'  # Stored in _data, marks dirty
            user.year = 1815  # Also stored in _data
        """
        raise NotImplementedError("Phase 1 stub")

    def __delattr__(self, name: str) -> None:
        """
        Handle attribute deletion for document fields.

        Removes a field from the internal _data cache and marks the object
        as dirty. On the next save(), this field will be removed from the
        Firestore document.

        Args:
            name: The attribute name to delete.

        Raises:
            AttributeError: If the attribute doesn't exist in _data or if
                           attempting to delete from a DELETED object.

        Side Effects:
            - Removes key from _data dictionary
            - Sets _dirty flag to True
            - Phase 2 will also add to _dirty_fields set for removal

        Example:
            user = db.doc('users/alovelace')
            del user.nickname  # Removes field, marks for deletion on save
            await user.save()  # Field removed from Firestore
        """
        raise NotImplementedError("Phase 1 stub")

    # =========================================================================
    # Core Lifecycle Methods
    # =========================================================================

    async def fetch(self, force: bool = False) -> 'FireObject':
        """
        Fetch document data from Firestore.

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
            google.cloud.exceptions.NotFound: If document doesn't exist in
                                             Firestore.

        State Transitions:
            ATTACHED -> LOADED: First fetch populates data
            LOADED -> LOADED: Refreshes data if force=True

        Side Effects:
            - Calls document_ref.get() from native library
            - Populates _data with document fields
            - Clears _dirty flag (data now matches Firestore)

        Example:
            user = db.doc('users/alovelace')  # ATTACHED
            await user.fetch()  # Now LOADED with data
            # ... make external changes in Firestore ...
            await user.fetch(force=True)  # Refresh data
        """
        raise NotImplementedError("Phase 1 stub")

    async def save(self, doc_id: Optional[str] = None) -> 'FireObject':
        """
        Save the object's data to Firestore.

        Creates or updates the Firestore document based on the object's
        current state. For DETACHED objects, creates a new document. For
        LOADED objects, performs a full overwrite (Phase 1) or partial
        update (Phase 2+) if dirty.

        Args:
            doc_id: Optional custom document ID. Only used when saving a
                   DETACHED object. If None, Firestore auto-generates an ID.

        Returns:
            Self, to allow method chaining.

        Raises:
            RuntimeError: If called on a DELETED object.
            ValueError: If doc_id contains invalid characters.

        State Transitions:
            DETACHED -> LOADED: Creates new document with doc_id or auto-ID
            LOADED -> LOADED: Updates document if dirty, no-op if clean

        Side Effects:
            - DETACHED: Calls collection_ref.document(doc_id).set() or
                       document_ref.set() for auto-ID
            - LOADED: Calls document_ref.set() (Phase 1 full overwrite)
            - Clears _dirty flag after successful save
            - Updates _doc_ref if transitioning from DETACHED

        Implementation Notes (Phase 1):
            - Uses simple boolean _dirty flag
            - Performs full document overwrites with .set()
            - Phase 2 will use _dirty_fields for partial updates with .update()

        Example:
            # Create new document
            user = collection.new()
            user.name = 'Ada'
            await user.save(doc_id='alovelace')  # DETACHED -> LOADED

            # Update existing
            user.year = 1816
            await user.save()  # Performs update
        """
        raise NotImplementedError("Phase 1 stub")

    async def delete(self) -> None:
        """
        Delete the document from Firestore.

        Removes the document from Firestore and transitions the object to
        DELETED state. After deletion, the object retains its ID and path
        for reference but cannot be modified or saved.

        Raises:
            ValueError: If called on a DETACHED object (no document to delete).
            RuntimeError: If called on an already-DELETED object.

        State Transitions:
            ATTACHED -> DELETED: Deletes document (data never loaded)
            LOADED -> DELETED: Deletes document (data was loaded)

        Side Effects:
            - Calls document_ref.delete() from native library
            - Transitions to DELETED state
            - Retains _doc_ref for ID/path reference

        Example:
            user = db.doc('users/alovelace')
            await user.delete()  # Document removed from Firestore
            print(user.state)  # State.DELETED
            print(user.id)  # Still accessible: 'alovelace'
        """
        raise NotImplementedError("Phase 1 stub")

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

        Side Effects:
            Creates FireObject with:
            - _doc_ref set to snapshot.reference
            - _data populated with snapshot.to_dict()
            - _state set to LOADED
            - _dirty set to False

        Implementation Notes:
            Phase 3 will auto-hydrate nested DocumentReference fields into
            ATTACHED FireObject instances for lazy loading of related documents.

        Example:
            # Hydrate from native query
            native_query = client.collection('users').where('year', '>', 1800)
            results = [FireObject.from_snapshot(snap)
                      for snap in native_query.stream()]

            # Hydrate from direct get
            snap = client.document('users/alovelace').get()
            user = FireObject.from_snapshot(snap)
        """
        raise NotImplementedError("Phase 1 stub")

    # =========================================================================
    # Special Methods
    # =========================================================================

    def __repr__(self) -> str:
        """
        Return a detailed string representation for debugging.

        Returns:
            String showing object state, path, and data status.

        Example:
            <FireObject state=LOADED path='users/alovelace' dirty=False>
        """
        raise NotImplementedError("Phase 1 stub")

    def __str__(self) -> str:
        """
        Return a human-readable string representation.

        Returns:
            String showing the document path or <detached> status.

        Example:
            'FireObject(users/alovelace)'
            'FireObject(<detached>)'
        """
        raise NotImplementedError("Phase 1 stub")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the object's data to a standard Python dictionary.

        Returns:
            A shallow copy of the internal _data dictionary.

        Raises:
            RuntimeError: If data hasn't been loaded yet (ATTACHED state).

        Example:
            user = db.doc('users/alovelace')
            await user.fetch()
            data = user.to_dict()
            # {'name': 'Ada Lovelace', 'year': 1815}
        """
        raise NotImplementedError("Phase 1 stub")
