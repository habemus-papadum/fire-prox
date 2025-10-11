from typing import Optional
from google.cloud.firestore_v1.client import Client
from .fire_object import FireObject
from .collection import FireCollection


class FireProx:
    """The main entry point for the FireProx library."""

    def __init__(self, client: Client):
        """
        Initializes the FireProx library.

        Args:
            client: The google-cloud-firestore client.
        """
        self._client = client

    def doc(self, path: str) -> FireObject:
        """
        Gets a FireObject for a document.

        Args:
            path: The path to the document.

        Returns:
            A FireObject.
        """
        doc_ref = self._client.document(path)
        return FireObject(doc_ref=doc_ref)

    def collection(self, path: str) -> FireCollection:
        """
        Gets a FireCollection for a collection.

        Args:
            path: The path to the collection.

        Returns:
            A FireCollection.
        """
        collection_ref = self._client.collection(path)
        return FireCollection(collection_ref=collection_ref)
