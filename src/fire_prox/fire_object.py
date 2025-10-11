from typing import Any, Dict, Optional, Set
from google.cloud.firestore_v1.document import DocumentReference
from google.cloud.firestore_v1.collection import CollectionReference
from .state import State


class FireObject:
    """A proxy for a Firestore document."""

    def __init__(self, doc_ref: Optional[DocumentReference] = None, initial_data: Optional[Dict[str, Any]] = None, collection_ref: Optional[CollectionReference] = None):
        """
        Initializes a FireObject.

        Args:
            doc_ref: The DocumentReference to the Firestore document.
            initial_data: Initial data for the object.
            collection_ref: The CollectionReference for detached objects.
        """
        self._doc_ref: Optional[DocumentReference] = doc_ref
        self._collection_ref: Optional[CollectionReference] = collection_ref
        self._data: Dict[str, Any] = initial_data or {}
        self._state: State = State.DETACHED if not doc_ref else State.ATTACHED
        self._dirty_fields: Set[str] = set(self._data.keys())

    def __getattr__(self, name: str) -> Any:
        """
        Gets an attribute from the object's data.

        Args:
            name: The name of the attribute.

        Returns:
            The value of the attribute.
        """
        if name in self._data:
            return self._data[name]
        # In Phase 1, we don't implement lazy loading.
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any):
        """
        Sets an attribute on the object's data.

        Args:
            name: The name of the attribute.
            value: The value of the attribute.
        """
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value
            self._dirty_fields.add(name)

    async def fetch(self):
        """Fetches the document from Firestore."""
        # In Phase 1, we don't implement fetching.
        pass

    async def delete(self):
        """Deletes the document from Firestore."""
        # In Phase 1, we don't implement deleting.
        pass

    async def save(self, doc_id: Optional[str] = None):
        """Saves the document to Firestore."""
        # In Phase 1, we don't implement saving.
        pass

    @property
    def state(self) -> State:
        """The state of the object."""
        return self._state

    def is_loaded(self) -> bool:
        """Returns True if the object's state is LOADED."""
        return self._state == State.LOADED

    def is_attached(self) -> bool:
        """Returns True if the object has a DocumentReference."""
        return self._doc_ref is not None

    def is_dirty(self) -> bool:
        """Returns True if any fields have been modified."""
        return bool(self._dirty_fields)

    def is_deleted(self) -> bool:
        """Returns True if the object's state is DELETED."""
        return self._state == State.DELETED
