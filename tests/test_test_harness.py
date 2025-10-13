"""Integration-style tests for the Firestore testing utilities."""

from fire_prox.testing import firestore_harness, testing_client


def _list_user_ids(client):
    """Return the sorted list of user document IDs in the emulator."""
    return sorted(doc.id for doc in client.collection("users").stream())


def test_fixture_provides_clean_state(firestore_test_harness):
    """The pytest fixture should start each test with an empty database."""
    client = testing_client()

    assert _list_user_ids(client) == []

    doc_ref = client.collection("users").document("fixture-user")
    doc_ref.set({"name": "Fixture User"})

    snapshot = doc_ref.get()
    assert snapshot.exists
    assert snapshot.to_dict() == {"name": "Fixture User"}


def test_context_manager_cleans_up_documents():
    """firestore_harness context manager should tear down created documents."""
    with firestore_harness():
        client = testing_client()
        doc_ref = client.collection("users").document("context-user")
        doc_ref.set({"name": "Context User"})
        assert _list_user_ids(client) == ["context-user"]

    # After the context exits, the database should be empty again.
    client = testing_client()
    assert _list_user_ids(client) == []
