"""
BaseFireProx: Shared logic for sync and async FireProx implementations.

This module contains the base class that implements all logic that is
identical between synchronous and asynchronous FireProx implementations.
"""

from typing import Any


class BaseFireProx:
    """
    Base class for FireProx implementations (sync and async).

    Contains all shared logic:
    - Client storage
    - Path validation
    - String representations

    Subclasses must implement:
    - doc() - creates FireObject/AsyncFireObject
    - collection() - creates FireCollection/AsyncFireCollection
    """

    def __init__(self, client: Any):
        """
        Initialize FireProx with a native Firestore client.

        Args:
            client: A configured google.cloud.firestore.Client or
                   google.cloud.firestore.AsyncClient instance.

        Note:
            Type checking is handled in subclasses since they know
            which client type to expect.
        """
        self._client = client

    # =========================================================================
    # Client Access (SHARED)
    # =========================================================================

    @property
    def native_client(self) -> Any:
        """
        Get the underlying google-cloud-firestore Client.

        Provides an "escape hatch" for users who need to perform operations
        not yet supported by FireProx or who want to use advanced native
        features like transactions, batched writes, or complex queries.

        Returns:
            The google.cloud.firestore.Client or AsyncClient instance.
        """
        return self._client

    @property
    def client(self) -> Any:
        """
        Alias for native_client. Get the underlying Firestore Client.

        Returns:
            The google.cloud.firestore.Client or AsyncClient instance.
        """
        return self._client

    # =========================================================================
    # Utility Methods (SHARED)
    # =========================================================================

    def _validate_path(self, path: str, path_type: str) -> None:
        """
        Validate a Firestore path.

        Internal utility to ensure paths conform to Firestore requirements.

        Args:
            path: The path to validate.
            path_type: Either 'document' or 'collection' for error messages.

        Raises:
            ValueError: If path is invalid (wrong segment count, invalid
                       characters, empty segments, etc.).
        """
        if not path:
            raise ValueError(f"Path cannot be empty for {path_type}")

        # Split path into segments
        segments = path.split('/')

        # Check for empty segments
        if any(not segment for segment in segments):
            raise ValueError(f"Path cannot contain empty segments: '{path}'")

        # Validate segment count based on type
        num_segments = len(segments)
        if path_type == 'document':
            if num_segments % 2 != 0:
                raise ValueError(
                    f"Document path must have even number of segments, got {num_segments}: '{path}'"
                )
        elif path_type == 'collection':
            if num_segments % 2 != 1:
                raise ValueError(
                    f"Collection path must have odd number of segments, got {num_segments}: '{path}'"
                )

    # =========================================================================
    # Special Methods (SHARED)
    # =========================================================================

    def __repr__(self) -> str:
        """
        Return a detailed string representation for debugging.

        Returns:
            String showing the project ID and database.
        """
        project = getattr(self._client, 'project', 'unknown')
        return f"<{type(self).__name__} project='{project}' database='(default)'>"

    def __str__(self) -> str:
        """
        Return a human-readable string representation.

        Returns:
            String showing the project ID.
        """
        project = getattr(self._client, 'project', 'unknown')
        return f"{type(self).__name__}({project})"
