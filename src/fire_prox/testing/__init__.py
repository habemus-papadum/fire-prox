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


@contextmanager
def temp_env(var, value):
    """
    A context manager to temporarily set an environment variable.

    Args:
        var (str): The name of the environment variable.
        value (str): The temporary value for the variable.
    """
    # Get the original value, which could be None if it doesn't exist
    original_value = os.getenv(var)

    # Set the new value. Note: environment variables must be strings.
    os.environ[var] = str(value)

    try:
        # Yield control to the code within the 'with' block
        yield
    finally:
        # This block executes after the 'with' block, even on exceptions
        if original_value is None:
            # If the variable didn't exist before, remove it
            del os.environ[var]
        else:
            # Otherwise, restore the original value
            os.environ[var] = original_value

def demo_client():
    # this is safe (but annoying) based on looking a Firestore Client code
    with temp_env('FIRESTORE_EMULATOR_HOST', DEMO_HOST):
        return testing_client()

def async_demo_client():
    # this is safe (but annoying) based on looking a Firestore Client code
    with temp_env("FIRESTORE_EMULATOR_HOST", DEMO_HOST):
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
