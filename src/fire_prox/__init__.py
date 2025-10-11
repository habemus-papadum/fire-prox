"""
FireProx: A schemaless, state-aware proxy library for Google Cloud Firestore.

FireProx provides a simplified, Pythonic interface for working with Firestore
during rapid prototyping. It wraps the official google-cloud-firestore client
with an intuitive object-oriented API that minimizes boilerplate and aligns
with Python's programming paradigms.

Main Components:
    FireProx: Main entry point for the library
    FireObject: State-aware proxy for Firestore documents
    FireCollection: Interface for working with collections
    State: Enum representing FireObject lifecycle states

Example Usage:
    from google.cloud import firestore
    from fire_prox import FireProx

    # Initialize
    native_client = firestore.Client(project='my-project')
    db = FireProx(native_client)

    # Create a document
    users = db.collection('users')
    user = users.new()
    user.name = 'Ada Lovelace'
    user.year = 1815
    await user.save()

    # Read a document (lazy loading)
    user = db.doc('users/alovelace')
    print(user.name)  # Automatically fetches data

    # Update a document
    user.year = 1816
    await user.save()

    # Delete a document
    await user.delete()
"""

from .fireprox import FireProx
from .fire_object import FireObject
from .fire_collection import FireCollection
from .state import State

__version__ = "0.1.0"

__all__ = [
    "FireProx",
    "FireObject",
    "FireCollection",
    "State",
]
