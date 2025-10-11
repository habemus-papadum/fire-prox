import os

from google.cloud import firestore

def test_fire_prox():

    os.environ["GRPC_VERBOSITY"] = "NONE"
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"


    # Initialize Firestore client (uses emulator if env var is set)
    db = firestore.Client(project="fire-prox-testing")

    # Add a document to the 'users' collection
    doc_ref = db.collection("users").document()
    doc_ref.set({"name": "Test User", "email": "testuser@example.com", "created": firestore.SERVER_TIMESTAMP})

    print(f"Added document with ID: {doc_ref.id}")

    ## query the database
    query = db.collection("users")
    results = query.stream()

    for doc in results:
        print(f"Document ID: {doc.id}, Data: {doc.to_dict()}")
