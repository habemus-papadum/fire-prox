"""
BaseFireObject: Shared logic for sync and async FireObject implementations.

This module contains the base class that implements all logic that is
identical between synchronous and asynchronous FireObject implementations.
"""

from typing import Optional, Any, Dict
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
        '_doc_ref', '_data', '_state', '_dirty', '_parent_collection',
        '_client', '_id', '_path'
    }

    def __init__(
        self,
        doc_ref: Optional[DocumentReference] = None,
        initial_state: Optional[State] = None,
        parent_collection: Optional[Any] = None
    ):
        """
        Initialize a FireObject.

        Args:
            doc_ref: Optional DocumentReference from native client.
            initial_state: Initial state (defaults to DETACHED if no doc_ref,
                          ATTACHED if doc_ref provided).
            parent_collection: Optional reference to parent FireCollection
                             (needed for save() on DETACHED objects).
        """
        # Set internal attributes directly to avoid __setattr__ logic
        object.__setattr__(self, '_doc_ref', doc_ref)
        object.__setattr__(self, '_data', {})
        object.__setattr__(self, '_parent_collection', parent_collection)

        # Determine initial state
        if initial_state is not None:
            object.__setattr__(self, '_state', initial_state)
        elif doc_ref is None:
            object.__setattr__(self, '_state', State.DETACHED)
        else:
            object.__setattr__(self, '_state', State.ATTACHED)

        # Dirty flag (DETACHED is always dirty)
        if self._state == State.DETACHED:
            object.__setattr__(self, '_dirty', True)
        else:
            object.__setattr__(self, '_dirty', False)

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
        return self._dirty

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
    # Attribute Handling (SHARED - but __getattr__ may need override)
    # =========================================================================

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Store attribute in _data dictionary and mark dirty.

        Internal attributes (starting with _) are stored directly on object.
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
            # Store in _data and mark dirty
            self._data[name] = value
            object.__setattr__(self, '_dirty', True)

    def __delattr__(self, name: str) -> None:
        """
        Remove field from _data and mark dirty.
        """
        if self._state == State.DELETED:
            raise AttributeError("Cannot delete attributes from a DELETED FireObject")

        if name not in self._data:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        del self._data[name]
        object.__setattr__(self, '_dirty', True)

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
            return f"<{type(self).__name__} DETACHED dirty={self._dirty}>"
        return f"<{type(self).__name__} {self._state.name} path='{self.path}' dirty={self._dirty}>"

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
        object.__setattr__(self, '_dirty', False)

    def _mark_dirty(self) -> None:
        """Mark object as dirty (has unsaved changes)."""
        object.__setattr__(self, '_dirty', True)

    def _transition_to_loaded(self, data: Dict[str, Any]) -> None:
        """
        Transition to LOADED state with given data.

        Args:
            data: Document data dictionary.
        """
        object.__setattr__(self, '_data', data)
        object.__setattr__(self, '_state', State.LOADED)
        object.__setattr__(self, '_dirty', False)

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
