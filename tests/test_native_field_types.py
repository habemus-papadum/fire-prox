"""Integration tests for native Firestore field types.

These tests ensure FireProx works seamlessly with native google-cloud-firestore
classes without requiring custom wrappers. The focus is on vector embeddings,
blobs, and server timestamp sentinels.
"""

from datetime import datetime, timezone

import pytest
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector


def _assert_vector_equal(actual: Vector, expected: Vector) -> None:
    """Helper to compare two native Vector instances."""
    assert isinstance(actual, Vector)
    assert actual.to_map_value() == expected.to_map_value()


def _assert_blob_equal(actual: bytes, expected: bytes) -> None:
    """Helper to compare Firestore blob values represented as bytes."""
    assert isinstance(actual, (bytes, bytearray))
    assert actual == expected
    assert bytes(actual) == bytes(expected)


def _assert_server_timestamp(value: datetime) -> None:
    """Validate that a value looks like a resolved server timestamp."""
    assert isinstance(value, datetime)
    # Firestore timestamps are timezone-aware UTC values.
    assert value.tzinfo is not None
    offset = value.tzinfo.utcoffset(value)
    assert offset is not None
    assert offset.total_seconds() == 0


def test_sync_vector_round_trip(db) -> None:
    collection = db.collection("native_vectors")
    doc = collection.new()
    native_vector = Vector([0.1, 0.2, 0.3])
    doc.embedding = native_vector
    doc.save()

    fetched = db.doc(doc.path)
    fetched.fetch()

    stored = fetched.embedding
    _assert_vector_equal(stored, native_vector)


def test_sync_blob_round_trip(db) -> None:
    collection = db.collection("native_blobs")
    doc = collection.new()
    payload = b"\x00native-bytes\xFF"
    doc.payload = payload
    doc.save()

    fetched = db.doc(doc.path)
    fetched.fetch()

    stored = fetched.payload
    _assert_blob_equal(stored, payload)


def test_sync_server_timestamp_round_trip(db) -> None:
    collection = db.collection("native_timestamps")
    doc = collection.new()
    doc.created_at = firestore.SERVER_TIMESTAMP
    doc.save()

    fetched = db.doc(doc.path)
    fetched.fetch()

    stored = fetched.created_at
    _assert_server_timestamp(stored)


@pytest.mark.asyncio
async def test_async_vector_round_trip(async_db) -> None:
    collection = async_db.collection("native_vectors_async")
    doc = collection.new()
    native_vector = Vector([0.4, 0.5, 0.6])
    doc.embedding = native_vector
    await doc.save()

    fetched = async_db.doc(doc.path)
    await fetched.fetch()

    stored = fetched.embedding
    _assert_vector_equal(stored, native_vector)


@pytest.mark.asyncio
async def test_async_blob_round_trip(async_db) -> None:
    collection = async_db.collection("native_blobs_async")
    doc = collection.new()
    payload = b"async-native-bytes"
    doc.payload = payload
    await doc.save()

    fetched = async_db.doc(doc.path)
    await fetched.fetch()

    stored = fetched.payload
    _assert_blob_equal(stored, payload)


@pytest.mark.asyncio
async def test_async_server_timestamp_round_trip(async_db) -> None:
    collection = async_db.collection("native_timestamps_async")
    doc = collection.new()
    doc.created_at = firestore.SERVER_TIMESTAMP
    await doc.save()

    fetched = async_db.doc(doc.path)
    await fetched.fetch()

    stored = fetched.created_at
    _assert_server_timestamp(stored)
