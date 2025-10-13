"""Tests for the Firestore test harness utilities."""

from fire_prox.testing import firestore_harness, testing_client


def test_firestore_harness_provides_clean_database():
    """The harness should clean documents before and after use."""
    with firestore_harness() as harness:
        client = testing_client()

        # Fixture should clean before yielding control
        assert list(client.collection("users").stream()) == []
        assert client.project == harness.project_id

        # Create a document to ensure data is written during the test
        doc_ref = client.collection("users").document("harness-user")
        doc_ref.set({"name": "Harness User", "language": "Python"})
        assert doc_ref.get().to_dict() == {"name": "Harness User", "language": "Python"}

    # Context manager cleanup runs after exiting the block
    post_client = testing_client()
    assert list(post_client.collection("users").stream()) == []
