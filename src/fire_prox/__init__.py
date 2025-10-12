"""
FireProx: A schemaless, state-aware proxy library for Google Cloud Firestore.

FireProx provides a simplified, Pythonic interface for working with Firestore
during rapid prototyping. It wraps the official google-cloud-firestore client
with an intuitive object-oriented API that minimizes boilerplate and aligns
with Python's programming paradigms.

Main Components:
    Synchronous API:
        FireProx: Main entry point for sync operations
        FireObject: State-aware proxy for Firestore documents
        FireCollection: Interface for working with collections

    Asynchronous API:
        AsyncFireProx: Main entry point for async operations
        AsyncFireObject: Async state-aware proxy for documents
        AsyncFireCollection: Async interface for collections

    Shared:
        State: Enum representing FireObject lifecycle states

Example Usage (Synchronous):
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
    user.save()

    # Read a document (lazy loading)
    user = db.doc('users/alovelace')
    print(user.name)  # Automatically fetches data

    # Update a document
    user.year = 1816
    user.save()

    # Delete a document
    user.delete()

Example Usage (Asynchronous):
    from google.cloud import firestore
    from fire_prox import AsyncFireProx

    # Initialize
    native_client = firestore.AsyncClient(project='my-project')
    db = AsyncFireProx(native_client)

    # Create a document
    users = db.collection('users')
    user = users.new()
    user.name = 'Ada Lovelace'
    user.year = 1815
    await user.save()

    # Read a document (explicit fetch required)
    user = db.doc('users/alovelace')
    await user.fetch()
    print(user.name)

    # Update a document
    user.year = 1816
    await user.save()

    # Delete a document
    await user.delete()
"""

# Synchronous API
from .fireprox import FireProx
from .fire_object import FireObject
from .fire_collection import FireCollection
from .fire_query import FireQuery

# Asynchronous API
from .async_fireprox import AsyncFireProx
from .async_fire_object import AsyncFireObject
from .async_fire_collection import AsyncFireCollection
from .async_fire_query import AsyncFireQuery

# Shared
from .state import State

__version__ = "0.5.0"

__all__ = [
    # Sync API
    "FireProx",
    "FireObject",
    "FireCollection",
    "FireQuery",
    # Async API
    "AsyncFireProx",
    "AsyncFireObject",
    "AsyncFireCollection",
    "AsyncFireQuery",
    # Shared
    "State",
]
