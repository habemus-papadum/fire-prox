"""
State management for FireObject instances.

This module defines the state machine that governs the lifecycle of FireObject
instances as they transition between different states of synchronization with
Firestore.
"""

from enum import Enum, auto


class State(Enum):
    """
    Represents the synchronization state of a FireObject with Firestore.

    The state machine ensures that FireObject instances correctly manage their
    lifecycle from creation through deletion, tracking whether data has been
    loaded from Firestore and whether local modifications need to be saved.

    States:
        DETACHED: Object exists only in Python memory with no Firestore reference.
                 This is the initial state for newly created documents that haven't
                 been saved yet. All data is considered "dirty" as it's new.

        ATTACHED: Object is linked to a Firestore document path and has a valid
                 DocumentReference, but the document's data has not yet been fetched.
                 This enables lazy loading - the reference exists but no network
                 request has been made yet.

        LOADED:  Object is fully synchronized with Firestore. It has a reference
                 and its data has been fetched from the server into the local cache.
                 This is the primary operational state for reading and modifying data.

        DELETED: Object represents a document that has been deleted from Firestore.
                 It retains its ID and path for reference but is marked as defunct
                 to prevent further modifications or save operations.

    State Transitions:
        DETACHED -> LOADED:  Via save() with optional doc_id
        ATTACHED -> LOADED:  Via fetch() or implicit fetch on attribute access
        LOADED -> LOADED:    Via save() (if dirty) or fetch() (refresh)
        LOADED -> DELETED:   Via delete()
    """

    DETACHED = auto()  # No Firestore reference, exists only in memory
    ATTACHED = auto()  # Has reference but data not yet fetched (lazy)
    LOADED = auto()    # Has reference and data is loaded
    DELETED = auto()   # Document has been deleted from Firestore

    def __str__(self) -> str:
        """Return a human-readable string representation of the state."""
        return self.name

    def __repr__(self) -> str:
        """Return a detailed representation of the state."""
        return f"State.{self.name}"
