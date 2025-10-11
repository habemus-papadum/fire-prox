import os

from google.cloud import firestore

from fire_prox.testing import firestore_test_harness  # noqa: F401 - registered as pytest fixture


def test_fire_prox(firestore_test_harness):
    os.environ["GRPC_VERBOSITY"] = "NONE"
    project_id = firestore_test_harness.project_id

    # Initialize Firestore client (uses emulator if env var is set)
    db = firestore.Client(project=project_id)

    # Add a document to the 'users' collection
    doc_ref = db.collection("users").document()
    doc_ref.set(
        {
            "name": "Test User",
            "email": "testuser@example.com",
            "created": firestore.SERVER_TIMESTAMP,
        }
    )

    print(f"Added document with ID: {doc_ref.id}")

    # query the database
    query = db.collection("users")
    results = query.stream()

    for doc in results:
        print(f"Document ID: {doc.id}, Data: {doc.to_dict()}")

    firestore_test_harness.cleanup()
    # Verify deletion
    results = list(db.collection("users").stream())
    assert len(results) == 0
    print("All documents deleted successfully.")
