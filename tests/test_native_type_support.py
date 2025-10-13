"""Tests for native Firestore type support without FireVector wrapper."""

from __future__ import annotations

import datetime as dt

import pytest
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector


def test_sync_vector_blob_and_server_timestamp_round_trip(db):
    """Ensure sync FireObjects handle native Vector, bytes, and SERVER_TIMESTAMP."""
    collection = db.collection('native_type_docs')
    doc = collection.new()

    embedding = Vector([0.1, 0.2, 0.3])
    blob = b"\x00fire-prox\x01"

    doc.embedding = embedding
    doc.payload = blob
    doc.last_updated = firestore.SERVER_TIMESTAMP
    doc.save()

    reloaded = db.doc(doc.path)

    fetched_embedding = reloaded.embedding
    fetched_blob = reloaded.payload
    fetched_timestamp = reloaded.last_updated

    assert isinstance(fetched_embedding, Vector)
    assert list(fetched_embedding) == [0.1, 0.2, 0.3]
    assert fetched_blob == blob
    assert isinstance(fetched_timestamp, dt.datetime)
    assert fetched_timestamp.tzinfo is not None


@pytest.mark.asyncio
async def test_async_vector_blob_and_server_timestamp_round_trip(async_db):
    """Ensure async FireObjects handle native Vector, bytes, and SERVER_TIMESTAMP."""
    collection = async_db.collection('native_type_docs_async')
    doc = collection.new()

    embedding = Vector([0.3, 0.2, 0.1])
    blob = b"\x02fire-prox\x03"

    doc.embedding = embedding
    doc.payload = blob
    doc.last_updated = firestore.SERVER_TIMESTAMP
    await doc.save()

    reloaded = async_db.doc(doc.path)
    await reloaded.fetch()

    fetched_embedding = reloaded.embedding
    fetched_blob = reloaded.payload
    fetched_timestamp = reloaded.last_updated

    assert isinstance(fetched_embedding, Vector)
    assert list(fetched_embedding) == [0.3, 0.2, 0.1]
    assert fetched_blob == blob
    assert isinstance(fetched_timestamp, dt.datetime)
    assert fetched_timestamp.tzinfo is not None
