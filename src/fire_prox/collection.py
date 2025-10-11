from typing import Any, Dict, Optional
from google.cloud.firestore_v1.collection import CollectionReference
from .fire_object import FireObject


class FireCollection:
    """A proxy for a Firestore collection."""

    def __init__(self, collection_ref: CollectionReference):
        """
        Initializes a FireCollection.

        Args:
            collection_ref: The CollectionReference to the Firestore collection.
        """
        self._collection_ref = collection_ref

    def new(self, initial_data: Optional[Dict[str, Any]] = None) -> FireObject:
        """
        Creates a new FireObject in the collection.

        Args:
            initial_data: Initial data for the new object.

        Returns:
            A new FireObject.
        """
        # The new object is DETACHED but knows which collection it belongs to.
        return FireObject(initial_data=initial_data or {}, collection_ref=self._collection_ref)
