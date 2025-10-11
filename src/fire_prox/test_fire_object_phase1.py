"""Unit tests for the Phase 1 FireObject implementation."""

from __future__ import annotations

import pytest

from fire_prox import (
    FireCollection,
    FireObjectDeletedError,
    FireObjectState,
    FireObjectStateError,
    FireProx,
)


class FakeSnapshot:
    """Mimics a Firestore ``DocumentSnapshot`` for testing purposes."""

    def __init__(self, data: dict[str, object], *, exists: bool = True) -> None:
        self._data = dict(data)
        self.exists = exists

    def to_dict(self) -> dict[str, object]:
        return dict(self._data)


class FakeDocumentReference:
    """Mimics a Firestore ``DocumentReference`` for testing purposes."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._snapshot = FakeSnapshot({})
        self.get_calls = 0
        self.set_payloads: list[dict[str, object]] = []
        self.delete_calls = 0

    def prime(self, data: dict[str, object], *, exists: bool = True) -> None:
        self._snapshot = FakeSnapshot(data, exists=exists)

    def get(self) -> FakeSnapshot:
        self.get_calls += 1
        return self._snapshot

    def set(self, payload: dict[str, object]) -> None:
        self.set_payloads.append(dict(payload))
        self._snapshot = FakeSnapshot(payload)

    def delete(self) -> None:
        self.delete_calls += 1


class FakeCollectionReference:
    """Mimics a Firestore ``CollectionReference`` for testing purposes."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._documents: dict[str, FakeDocumentReference] = {}

    def document(self, document_id: str | None = None) -> FakeDocumentReference:
        if document_id is None:
            document_id = f"auto_{len(self._documents) + 1}"
        if document_id not in self._documents:
            self._documents[document_id] = FakeDocumentReference(f"{self.path}/{document_id}")
        return self._documents[document_id]


class FakeClient:
    """Mimics the google-cloud-firestore client for testing purposes."""

    def __init__(self) -> None:
        self._documents: dict[str, FakeDocumentReference] = {}
        self._collections: dict[str, FakeCollectionReference] = {}

    def document(self, path: str) -> FakeDocumentReference:
        if path not in self._documents:
            self._documents[path] = FakeDocumentReference(path)
        return self._documents[path]

    def collection(self, path: str) -> FakeCollectionReference:
        if path not in self._collections:
            self._collections[path] = FakeCollectionReference(path)
        return self._collections[path]


@pytest.fixture()
def fake_client() -> FakeClient:
    return FakeClient()


def test_fetch_populates_data_and_transitions_state(fake_client: FakeClient) -> None:
    doc_ref = fake_client.document("users/alice")
    doc_ref.prime({"name": "Alice", "age": 42})
    fire_prox = FireProx(fake_client)

    user = fire_prox.doc("users/alice")
    assert user.state is FireObjectState.ATTACHED

    user.fetch()
    assert user.state is FireObjectState.LOADED
    assert user.name == "Alice"
    assert user.age == 42


def test_lazy_attribute_access_triggers_fetch(fake_client: FakeClient) -> None:
    doc_ref = fake_client.document("users/bob")
    doc_ref.prime({"nickname": "Bobby"})
    user = FireProx(fake_client).doc("users/bob")

    assert doc_ref.get_calls == 0
    assert user.nickname == "Bobby"
    assert doc_ref.get_calls == 1


def test_attribute_assignment_is_persisted_on_save(fake_client: FakeClient) -> None:
    doc_ref = fake_client.document("users/carla")
    doc_ref.prime({"name": "Carla"})
    user = FireProx(fake_client).doc("users/carla")
    user.fetch()

    user.favorite_color = "teal"
    user.save()

    assert user.state is FireObjectState.LOADED
    assert doc_ref.set_payloads[-1]["favorite_color"] == "teal"


def test_save_detached_document_uses_collection_context(fake_client: FakeClient) -> None:
    collection = FireProx(fake_client).collection("projects")
    project = collection.new({"name": "Fire-Prox"}, document_id="library")

    project.save()

    doc_ref = fake_client.collection("projects").document("library")
    assert doc_ref.set_payloads[-1]["name"] == "Fire-Prox"
    assert project.state is FireObjectState.LOADED


def test_delete_transitions_object_to_deleted(fake_client: FakeClient) -> None:
    doc_ref = fake_client.document("users/dora")
    doc_ref.prime({"status": "active"})
    user = FireProx(fake_client).doc("users/dora")
    user.fetch()

    user.delete()
    assert user.state is FireObjectState.DELETED
    assert doc_ref.delete_calls == 1

    with pytest.raises(FireObjectDeletedError):
        user.status = "inactive"


def test_fetch_on_detached_object_raises(fake_client: FakeClient) -> None:
    collection = FireCollection(fake_client.collection("users"))
    user = collection.new({"name": "Detached"})

    with pytest.raises(FireObjectStateError):
        user.fetch()


def test_delete_on_detached_object_raises(fake_client: FakeClient) -> None:
    collection = FireCollection(fake_client.collection("users"))
    user = collection.new({"name": "Detached"})

    with pytest.raises(FireObjectStateError):
        user.delete()


def test_missing_attribute_raises_after_fetch(fake_client: FakeClient) -> None:
    doc_ref = fake_client.document("users/eric")
    doc_ref.prime({"name": "Eric"})
    user = FireProx(fake_client).doc("users/eric")
    user.fetch()

    with pytest.raises(AttributeError):
        _ = user.non_existent
