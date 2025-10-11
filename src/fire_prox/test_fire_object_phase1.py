"""Unit tests for Phase 1 FireObject functionality."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest import mock

import pytest

from fire_prox import FireCollection, FireObject, FireObjectState, FireProx


class DummySnapshot:
    """Simple helper to mimic the Firestore ``DocumentSnapshot`` API."""

    def __init__(self, data: dict[str, Any], *, exists: bool = True) -> None:
        self._data = data
        self.exists = exists

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)


@pytest.fixture
def mock_client() -> mock.Mock:
    return mock.Mock(name="FirestoreClient")


def test_doc_returns_attached_fire_object(mock_client: mock.Mock) -> None:
    doc_ref = mock.Mock(name="DocumentReference")
    mock_client.document.return_value = doc_ref

    db = FireProx(mock_client)
    obj = db.doc("users/alovelace")

    assert isinstance(obj, FireObject)
    assert obj.state is FireObjectState.ATTACHED
    assert obj.reference is doc_ref
    mock_client.document.assert_called_once_with("users/alovelace")


def test_lazy_fetch_on_attribute_access(mock_client: mock.Mock) -> None:
    snapshot = DummySnapshot({"name": "Ada", "year": 1815})
    doc_ref = mock.Mock(name="DocumentReference", get=mock.Mock(return_value=snapshot))
    mock_client.document.return_value = doc_ref

    user = FireProx(mock_client).doc("users/alovelace")

    assert user.state is FireObjectState.ATTACHED
    assert user.name == "Ada"
    assert user.state is FireObjectState.LOADED
    doc_ref.get.assert_called_once_with()


def test_fetch_refreshes_data_and_resets_dirty(mock_client: mock.Mock) -> None:
    first_snapshot = DummySnapshot({"name": "Ada"})
    second_snapshot = DummySnapshot({"name": "Ada", "year": 1815})
    doc_ref = mock.Mock(name="DocumentReference")
    doc_ref.get.side_effect = [first_snapshot, second_snapshot]
    mock_client.document.return_value = doc_ref

    user = FireProx(mock_client).doc("users/alovelace")
    user.fetch()
    assert user.to_dict() == {"name": "Ada"}
    assert user.is_loaded()
    assert not user.is_dirty()

    user.year = 1815
    assert user.is_dirty()

    user.fetch()
    assert user.to_dict() == {"name": "Ada", "year": 1815}
    assert not user.is_dirty()


def test_save_creates_new_document_with_auto_id(mock_client: mock.Mock) -> None:
    collection_ref = mock.Mock(name="CollectionReference")
    doc_ref = mock.Mock(name="DocumentReference")
    collection_ref.document.return_value = doc_ref

    collection = FireCollection(collection_ref)
    post = collection.new()
    post.title = "Analytical Engine"
    post.year = 1843

    post.save()

    collection_ref.document.assert_called_once_with()
    doc_ref.set.assert_called_once_with({"title": "Analytical Engine", "year": 1843})
    assert post.state is FireObjectState.LOADED
    assert not post.is_dirty()


def test_save_creates_new_document_with_custom_id(mock_client: mock.Mock) -> None:
    collection_ref = mock.Mock(name="CollectionReference")
    doc_ref = mock.Mock(name="DocumentReference")
    collection_ref.document.return_value = doc_ref

    post = FireCollection(collection_ref).new()
    post.title = "Notes"

    post.save(doc_id="alovelace")

    collection_ref.document.assert_called_once_with("alovelace")
    doc_ref.set.assert_called_once_with({"title": "Notes"})
    assert post.state is FireObjectState.LOADED


def test_delete_attached_object(mock_client: mock.Mock) -> None:
    doc_ref = mock.Mock(name="DocumentReference")
    mock_client.document.return_value = doc_ref
    obj = FireProx(mock_client).doc("users/alovelace")

    obj.delete()

    doc_ref.delete.assert_called_once_with()
    assert obj.is_deleted()
    assert obj.to_dict() == {}


def test_delete_detached_object_without_reference() -> None:
    obj = FireObject()
    obj.name = "Ada"
    assert obj.is_dirty()

    obj.delete()

    assert obj.is_deleted()
    assert obj.to_dict() == {}
    assert not obj.is_dirty()


def test_fire_collection_doc_returns_attached_object(mock_client: mock.Mock) -> None:
    collection_ref = mock.Mock(name="CollectionReference")
    doc_ref = mock.Mock(name="DocumentReference")
    collection_ref.document.return_value = doc_ref

    collection = FireCollection(collection_ref)
    obj = collection.doc("alovelace")

    assert obj.state is FireObjectState.ATTACHED
    assert obj.reference is doc_ref


@pytest.mark.parametrize("method_name", ["fetch_async", "save_async", "delete_async"])
def test_async_wrappers_delegate_to_thread(method_name: str, mock_client: mock.Mock) -> None:
    doc_ref = mock.Mock(name="DocumentReference")
    doc_ref.get.return_value = DummySnapshot({})
    mock_client.document.return_value = doc_ref
    obj = FireProx(mock_client).doc("users/alovelace")

    async def fake_to_thread(func, /, *args, **kwargs):
        func(*args, **kwargs)

    with mock.patch("fire_prox.__init__.asyncio.to_thread", side_effect=fake_to_thread) as patched:
        coroutine = getattr(obj, method_name)()
        asyncio.run(coroutine)

    assert patched.called
    called_func = patched.call_args.args[0]
    assert callable(called_func)


