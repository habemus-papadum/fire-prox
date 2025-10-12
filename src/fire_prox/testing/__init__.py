import os
from contextlib import contextmanager
from typing import Iterator, Optional

import google.cloud.firestore as firestore
import requests

from fire_prox.fireprox import FireProx
from fire_prox.async_fireprox import AsyncFireProx
from google.cloud.firestore import Client 
from google.cloud.firestore_v1 import AsyncClient

DEFAULT_PROJECT_ID = "fire-prox-testing"

def testing_client():
    """Create a synchronous Firestore client configured to connect to the emulator."""
    return firestore.Client(
        project=DEFAULT_PROJECT_ID,
    )


def async_testing_client():
    """Create an asynchronous Firestore client configured to connect to the emulator."""
    return firestore.AsyncClient(
        project=DEFAULT_PROJECT_ID,
    )

DEMO_HOST = "localhost:9090"


def demo_client():
    """
    Create a demo Firestore client.

    If NOTEBOOK_CI environment variable is set, returns a standard testing client.
    Otherwise, returns a client configured for the developer emulator (port 9090).
    """
    # In CI/test environment, use standard test client
    if os.getenv('NOTEBOOK_CI'):
        return testing_client()

    # For local development, use developer emulator with UI
    os.environ['FIRESTORE_EMULATOR_HOST'] = DEMO_HOST
    return testing_client()

def async_demo_client():
    """
    Create an async demo Firestore client.

    If NOTEBOOK_CI environment variable is set, returns a standard async testing client.
    Otherwise, returns a client configured for the developer emulator (port 9090).
    """
    # In CI/test environment, use standard async test client
    if os.getenv('NOTEBOOK_CI'):
        return async_testing_client()

    # For local development, use developer emulator with UI
    os.environ["FIRESTORE_EMULATOR_HOST"] = DEMO_HOST
    return async_testing_client()

class FirestoreProjectCleanupError(RuntimeError):
    """Raised when the Firestore emulator project could not be deleted."""


def _get_emulator_host(
    db_or_client: firestore.Client | firestore.AsyncClient | FireProx | AsyncFireProx | None = None,
) -> str:
    """Determine the Firestore emulator host from the given client or environment."""
    if db_or_client is not None:
        if isinstance(db_or_client, (firestore.Client, firestore.AsyncClient)):
            if db_or_client._emulator_host:  # type: ignore[attr-defined]
                return db_or_client._emulator_host  # type: ignore[attr-defined]
            else:
                raise EnvironmentError("The provided Firestore client is not configured to use the emulator.")
        elif isinstance(db_or_client, (FireProx, AsyncFireProx)):
            if db_or_client._client._emulator_host:  # type: ignore[attr-defined]
                return db_or_client._client._emulator_host  # type: ignore[attr-defined]
            else:
                raise EnvironmentError("The provided FireProx instance is not configured to use the emulator.")
    host = os.getenv("FIRESTORE_EMULATOR_HOST")
    if not host:
        raise EnvironmentError("FIRESTORE_EMULATOR_HOST environment variable is not set.")
    return host


def cleanup_firestore(
    project_id: str = DEFAULT_PROJECT_ID,
    db_or_client: firestore.Client | firestore.AsyncClient | FireProx | AsyncFireProx | None = None
) -> None:
    """Delete all documents in the given project on the Firestore emulator."""
    emulator_host = _get_emulator_host(db_or_client)
    url = f"http://{emulator_host}/emulator/v1/projects/{project_id}/databases/(default)/documents"
    try:
        response = requests.delete(url, timeout=10)
    except requests.RequestException as exc:
        raise FirestoreProjectCleanupError(f"Failed to connect to Firestore emulator at {url}") from exc

    if not (200 <= response.status_code < 300):
        raise FirestoreProjectCleanupError(
            f"Firestore emulator returned {response.status_code} when deleting project {project_id}: {response.text}"
        )


class FirestoreTestHarness:
    """Utility that cleans up the Firestore emulator project before and after tests."""

    def __init__(self, project_id: str = DEFAULT_PROJECT_ID):
        self.project_id = project_id

    def cleanup(self) -> None:
        cleanup_firestore(self.project_id)

    def setup(self) -> None:
        self.cleanup()

    def teardown(self) -> None:
        self.cleanup()

    def __enter__(self) -> "FirestoreTestHarness":
        self.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        self.teardown()
        return None


@contextmanager
def firestore_harness(project_id: str = DEFAULT_PROJECT_ID) -> Iterator[FirestoreTestHarness]:
    """Context manager that ensures Firestore cleanup in setup/teardown."""
    harness = FirestoreTestHarness(project_id=project_id)
    with harness:
        yield harness


try:
    import pytest
except ModuleNotFoundError:  # pragma: no cover - pytest is optional at runtime
    pytest = None  # type: ignore[assignment]
else:

    @pytest.fixture(scope="function")
    def firestore_test_harness() -> Iterator[FirestoreTestHarness]:
        """Pytest fixture that yields a FirestoreTestHarness."""
        with firestore_harness() as harness:
            yield harness
