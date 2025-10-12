"""
BaseFireObject: Shared logic for sync and async FireObject implementations.

This module contains the base class that implements all logic that is
identical between synchronous and asynchronous FireObject implementations.
"""

from typing import Optional, Any, Dict, Set
from google.cloud.firestore_v1.document import DocumentReference, DocumentSnapshot
from .state import State


class BaseFireObject:
    """
    Base class for FireObject implementations (sync and async).

    Contains all shared logic:
    - State management
    - State inspection methods
    - Dirty tracking
    - Data dictionary management
    - Property accessors
    - String representations

    Subclasses must implement:
    - fetch() - with appropriate sync/async signature
    - save() - with appropriate sync/async signature
    - delete() - with appropriate sync/async signature
    - __getattr__() - may need async support for lazy loading
    """

    # Class-level constants for internal attribute names
    _INTERNAL_ATTRS = {
        '_doc_ref', '_sync_doc_ref', '_sync_client', '_data', '_state', '_dirty_fields',
        '_deleted_fields', '_atomic_ops', '_parent_collection', '_client', '_id', '_path'
    }

    def __init__(
        self,
        doc_ref: Optional[DocumentReference] = None,
        initial_state: Optional[State] = None,
        parent_collection: Optional[Any] = None,
        sync_doc_ref: Optional[DocumentReference] = None,
        sync_client: Optional[Any] = None
    ):
        """
        Initialize a FireObject.

        Args:
            doc_ref: Optional DocumentReference from native client.
            initial_state: Initial state (defaults to DETACHED if no doc_ref,
                          ATTACHED if doc_ref provided).
            parent_collection: Optional reference to parent FireCollection
                             (needed for save() on DETACHED objects).
            sync_doc_ref: Optional sync DocumentReference (for async lazy loading).
            sync_client: Optional sync Firestore Client (for async subcollections).
        """
        # Set internal attributes directly to avoid __setattr__ logic
        object.__setattr__(self, '_doc_ref', doc_ref)
        object.__setattr__(self, '_sync_doc_ref', sync_doc_ref)
        object.__setattr__(self, '_sync_client', sync_client)
        object.__setattr__(self, '_data', {})
        object.__setattr__(self, '_parent_collection', parent_collection)

        # Determine initial state
        if initial_state is not None:
            object.__setattr__(self, '_state', initial_state)
        elif doc_ref is None:
            object.__setattr__(self, '_state', State.DETACHED)
        else:
            object.__setattr__(self, '_state', State.ATTACHED)

        # Field-level dirty tracking (Phase 2)
        # Track which fields have been modified or deleted since last save/fetch
        object.__setattr__(self, '_dirty_fields', set())
        object.__setattr__(self, '_deleted_fields', set())

        # Atomic operations tracking (Phase 2)
        # Store atomic operations (ArrayUnion, ArrayRemove, Increment) to apply on save
        object.__setattr__(self, '_atomic_ops', {})

    # =========================================================================
    # State Inspection (SHARED)
    # =========================================================================

    @property
    def state(self) -> State:
        """Get current state of the object."""
        return self._state

    def is_detached(self) -> bool:
        """Check if object is in DETACHED state."""
        return self._state == State.DETACHED

    def is_attached(self) -> bool:
        """Check if object has a DocumentReference (ATTACHED or LOADED)."""
        return self._state in (State.ATTACHED, State.LOADED)

    def is_loaded(self) -> bool:
        """Check if object is in LOADED state."""
        return self._state == State.LOADED

    def is_deleted(self) -> bool:
        """Check if object is in DELETED state."""
        return self._state == State.DELETED

    def is_dirty(self) -> bool:
        """Check if object has unsaved changes."""
        if self._state == State.DETACHED:
            return True  # DETACHED is always dirty
        return (len(self._dirty_fields) > 0 or
                len(self._deleted_fields) > 0 or
                len(self._atomic_ops) > 0)

    @property
    def dirty_fields(self) -> Set[str]:
        """Get the set of modified field names (Phase 2)."""
        return self._dirty_fields.copy()

    @property
    def deleted_fields(self) -> Set[str]:
        """Get the set of deleted field names (Phase 2)."""
        return self._deleted_fields.copy()

    # =========================================================================
    # Document Identity (SHARED)
    # =========================================================================

    @property
    def id(self) -> Optional[str]:
        """Get document ID, or None if DETACHED."""
        return self._doc_ref.id if self._doc_ref else None

    @property
    def path(self) -> Optional[str]:
        """Get full document path, or None if DETACHED."""
        return self._doc_ref.path if self._doc_ref else None

    # =========================================================================
    # Subcollections (Phase 2)
    # =========================================================================

    def collection(self, name: str) -> Any:
        """
        Get a subcollection reference for this document.

        Phase 2 feature. Returns a collection reference for a subcollection
        under this document, enabling hierarchical data structures.

        Args:
            name: Name of the subcollection.

        Returns:
            FireCollection or AsyncFireCollection instance for the subcollection.

        Raises:
            ValueError: If called on a DETACHED object (no document path yet).
            RuntimeError: If called on a DELETED object.

        Example:
            user = db.doc('users/alovelace')
            posts = user.collection('posts')  # Gets 'users/alovelace/posts'
            new_post = posts.new()
            new_post.title = "On Analytical Engines"
            new_post.save()
        """
        self._validate_not_detached("collection()")
        self._validate_not_deleted("collection()")

        # Get subcollection reference from document reference
        subcollection_ref = self._doc_ref.collection(name)

        # Import here to avoid circular dependency
        from .fire_collection import FireCollection
        from .async_fire_collection import AsyncFireCollection

        # Return appropriate collection type based on client type
        # The concrete class will override this if needed
        if hasattr(self._doc_ref, '__class__') and 'Async' in self._doc_ref.__class__.__name__:
            # Get sync client if available for async lazy loading
            sync_collection_ref = None
            if hasattr(self, '_sync_doc_ref') and self._sync_doc_ref:
                sync_collection_ref = self._sync_doc_ref.collection(name)

            return AsyncFireCollection(
                subcollection_ref,
                client=None,  # Will be inferred from ref
                sync_client=self._sync_client if hasattr(self, '_sync_client') else None
            )
        else:
            return FireCollection(subcollection_ref, client=None)

    # =========================================================================
    # Atomic Operations (Phase 2)
    # =========================================================================

    def array_union(self, field: str, values: list) -> None:
        """
        Mark field for ArrayUnion operation.

        Phase 2 feature. ArrayUnion adds elements to an array field without
        reading the document first. If the array doesn't exist, it creates it.
        Duplicate values are automatically deduplicated.

        Args:
            field: The field name to apply ArrayUnion to.
            values: List of values to add to the array.

        Raises:
            RuntimeError: If called on a DELETED object.

        Example:
            user = db.doc('users/ada')
            user.array_union('tags', ['python', 'firestore'])
            user.save()
        """
        self._validate_not_deleted("array_union()")

        # Store the operation
        from google.cloud import firestore
        self._atomic_ops[field] = firestore.ArrayUnion(values)

    def array_remove(self, field: str, values: list) -> None:
        """
        Mark field for ArrayRemove operation.

        Phase 2 feature. ArrayRemove removes specified elements from an array
        field without reading the document first.

        Args:
            field: The field name to apply ArrayRemove to.
            values: List of values to remove from the array.

        Raises:
            RuntimeError: If called on a DELETED object.

        Example:
            user = db.doc('users/ada')
            user.array_remove('tags', ['deprecated'])
            user.save()
        """
        self._validate_not_deleted("array_remove()")

        # Store the operation
        from google.cloud import firestore
        self._atomic_ops[field] = firestore.ArrayRemove(values)

    def increment(self, field: str, value: float) -> None:
        """
        Mark field for Increment operation.

        Phase 2 feature. Increment atomically increments a numeric field by the
        given value without reading the document first. If the field doesn't
        exist, it treats it as 0.

        Args:
            field: The field name to increment.
            value: The amount to increment by (can be negative to decrement).

        Raises:
            RuntimeError: If called on a DELETED object.

        Example:
            user = db.doc('users/ada')
            user.increment('view_count', 1)
            user.increment('score', -5)  # Decrement by 5
            user.save()
        """
        self._validate_not_deleted("increment()")

        # Store the operation
        from google.cloud import firestore
        self._atomic_ops[field] = firestore.Increment(value)

    # =========================================================================
    # Attribute Handling (SHARED - but __getattr__ may need override)
    # =========================================================================

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Store attribute in _data dictionary and track in dirty fields.

        Internal attributes (starting with _) are stored directly on object.

        Phase 2: Track field-level changes for efficient partial updates.
        """
        # Internal attributes bypass _data storage
        if name in self._INTERNAL_ATTRS:
            object.__setattr__(self, name, value)
            return

        # Cannot modify DELETED objects
        if hasattr(self, '_state') and self._state == State.DELETED:
            raise AttributeError("Cannot modify a DELETED FireObject")

        # Initialize phase - before _data exists
        if not hasattr(self, '_data'):
            object.__setattr__(self, name, value)
        else:
            # Store in _data and track in dirty fields
            self._data[name] = value
            self._dirty_fields.add(name)
            # If this field was marked for deletion, remove it from deleted set
            self._deleted_fields.discard(name)

    def __delattr__(self, name: str) -> None:
        """
        Remove field from _data and track in deleted fields.

        Phase 2: Track deletions for efficient partial updates with DELETE_FIELD.
        """
        if self._state == State.DELETED:
            raise AttributeError("Cannot delete attributes from a DELETED FireObject")

        if name not in self._data:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        del self._data[name]
        # Track deletion for partial update
        self._deleted_fields.add(name)
        # Remove from dirty fields if it was there
        self._dirty_fields.discard(name)

    # =========================================================================
    # Utility Methods (SHARED)
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """
        Return shallow copy of internal data.

        Returns:
            Dictionary containing all document fields.

        Raises:
            RuntimeError: If object is in ATTACHED state (data not loaded).
        """
        if self._state == State.ATTACHED:
            raise RuntimeError("Cannot call to_dict() on ATTACHED FireObject. Call fetch() first.")

        return dict(self._data)

    def __repr__(self) -> str:
        """Return detailed string representation."""
        if self._state == State.DETACHED:
            return f"<{type(self).__name__} DETACHED dirty_fields={len(self._dirty_fields)}>"
        dirty_count = len(self._dirty_fields) + len(self._deleted_fields)
        return f"<{type(self).__name__} {self._state.name} path='{self.path}' dirty_fields={dirty_count}>"

    def __str__(self) -> str:
        """Return human-readable string representation."""
        if self._state == State.DETACHED:
            return f"{type(self).__name__}(detached)"
        return f"{type(self).__name__}({self.path})"

    # =========================================================================
    # Protected Helper Methods (SHARED)
    # =========================================================================

    def _validate_not_deleted(self, operation: str) -> None:
        """
        Validate that object is not in DELETED state.

        Args:
            operation: Name of operation being attempted.

        Raises:
            RuntimeError: If object is DELETED.
        """
        if self._state == State.DELETED:
            raise RuntimeError(f"Cannot {operation} on a DELETED FireObject")

    def _validate_not_detached(self, operation: str) -> None:
        """
        Validate that object is not in DETACHED state.

        Args:
            operation: Name of operation being attempted.

        Raises:
            ValueError: If object is DETACHED.
        """
        if self._state == State.DETACHED:
            raise ValueError(f"Cannot {operation} on a DETACHED FireObject (no DocumentReference)")

    def _mark_clean(self) -> None:
        """Mark object as clean (no unsaved changes)."""
        self._dirty_fields.clear()
        self._deleted_fields.clear()
        self._atomic_ops.clear()

    def _mark_dirty(self) -> None:
        """Mark object as dirty (has unsaved changes).

        Note: In Phase 2, this is a fallback for cases where we don't know
        which specific fields changed. Prefer tracking specific fields when possible.
        """
        # Add all current fields to dirty set as a fallback
        self._dirty_fields.update(self._data.keys())

    def _transition_to_loaded(self, data: Dict[str, Any]) -> None:
        """
        Transition to LOADED state with given data.

        Args:
            data: Document data dictionary.
        """
        object.__setattr__(self, '_data', data)
        object.__setattr__(self, '_state', State.LOADED)
        # Clear dirty tracking (Phase 2: field-level tracking)
        self._dirty_fields.clear()
        self._deleted_fields.clear()
        self._atomic_ops.clear()

    def _transition_to_deleted(self) -> None:
        """Transition to DELETED state."""
        object.__setattr__(self, '_state', State.DELETED)

    @classmethod
    def _create_from_snapshot_base(
        cls,
        snapshot: DocumentSnapshot,
        parent_collection: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Extract data for creating FireObject from snapshot.

        This is shared logic for from_snapshot() factory methods.

        Args:
            snapshot: DocumentSnapshot from native API.
            parent_collection: Optional parent collection reference.

        Returns:
            Dictionary with initialization parameters.

        Raises:
            ValueError: If snapshot doesn't exist.
        """
        if not snapshot.exists:
            raise ValueError("Cannot create FireObject from non-existent snapshot")

        return {
            'doc_ref': snapshot.reference,
            'initial_state': State.LOADED,
            'parent_collection': parent_collection,
            'data': snapshot.to_dict() or {}
        }
