import os
from contextlib import contextmanager
from typing import Iterator, Optional

import google.cloud.firestore as firestore
import requests

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


class FirestoreProjectCleanupError(RuntimeError):
    """Raised when the Firestore emulator project could not be deleted."""


def _get_emulator_host() -> str:
    host = os.getenv("FIRESTORE_EMULATOR_HOST")
    if not host:
        raise EnvironmentError("FIRESTORE_EMULATOR_HOST environment variable is not set.")
    return host


def cleanup_firestore(project_id: str = DEFAULT_PROJECT_ID) -> None:
    """Delete all documents in the given project on the Firestore emulator."""
    emulator_host = _get_emulator_host()
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
