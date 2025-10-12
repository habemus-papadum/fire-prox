"""
ProxiedMap: Dictionary proxy with mutation tracking.

This module implements a transparent proxy for dictionaries that tracks mutations
and reports them to parent FireObject instances. When any nested value is modified,
the entire top-level field is marked as dirty for conservative saving.

Phase 3 feature.
"""

from collections.abc import MutableMapping
from typing import Any, Iterator, Optional, TYPE_CHECKING

from .firestore_constraints import (
    validate_field_name,
    validate_nesting_depth,
    FirestoreConstraintError
)

if TYPE_CHECKING:
    from .base_fire_object import BaseFireObject


def _wrap_value(
    value: Any,
    parent: 'BaseFireObject',
    field_path: str,
    depth: int
) -> Any:
    """
    Recursively wrap dictionaries and lists in proxy objects.

    Args:
        value: Value to potentially wrap.
        parent: Parent FireObject that owns this data.
        field_path: Dot-separated path to this value from the root object.
        depth: Current nesting depth (for validation).

    Returns:
        ProxiedMap if value is dict, ProxiedList if value is list, otherwise value unchanged.

    Raises:
        FirestoreConstraintError: If nesting depth exceeds limit.
    """
    # Validate depth before wrapping
    validate_nesting_depth(depth, context=f"at path '{field_path}'")

    if isinstance(value, dict):
        # Import here to avoid circular dependency
        return ProxiedMap(value, parent, field_path, depth)
    elif isinstance(value, list):
        # Import here to avoid circular dependency
        from .proxied_list import ProxiedList
        return ProxiedList(value, parent, field_path, depth)
    else:
        return value


def _unwrap_value(value: Any) -> Any:
    """
    Recursively unwrap proxy objects back to plain Python types.

    Args:
        value: Value to potentially unwrap.

    Returns:
        Plain dict if ProxiedMap, plain list if ProxiedList, otherwise value unchanged.
    """
    # Check by class name to avoid circular imports
    class_name = type(value).__name__

    if class_name == 'ProxiedMap':
        return {key: _unwrap_value(val) for key, val in value.items()}
    elif class_name == 'ProxiedList':
        return [_unwrap_value(item) for item in value]
    else:
        return value


class ProxiedMap(MutableMapping):
    """
    Dictionary proxy that tracks mutations and enforces Firestore constraints.

    This class wraps a dictionary and transparently tracks any modifications,
    reporting them to the parent FireObject. All nested dictionaries and lists
    are recursively wrapped in proxies.

    When any mutation occurs (setitem, delitem, etc.), the top-level field is
    marked as dirty in the parent FireObject, causing the entire structure to be
    saved on the next save() call.

    Phase 3 feature.

    Example:
        user = db.doc('users/ada')
        user.settings = {'notifications': {'email': True, 'sms': False}}
        user.save()

        # Nested mutation automatically tracked
        user.settings['notifications']['email'] = False
        # user is now dirty, will save entire 'settings' field

    Attributes:
        _data: Internal dictionary storage.
        _parent: Parent FireObject that owns this data.
        _field_path: Top-level field path (e.g., 'settings').
        _depth: Current nesting depth (for constraint validation).
    """

    def __init__(
        self,
        data: dict,
        parent: 'BaseFireObject',
        field_path: str,
        depth: int = 0
    ):
        """
        Initialize ProxiedMap.

        Args:
            data: Dictionary to wrap.
            parent: Parent FireObject instance.
            field_path: Field path from root object (top-level field name).
            depth: Current nesting depth (0-indexed).

        Raises:
            FirestoreConstraintError: If any field name is invalid or depth exceeds limit.
        """
        self._data = {}
        self._parent = parent
        self._field_path = field_path
        self._depth = depth

        # Validate and recursively wrap initial data
        for key, value in data.items():
            validate_field_name(key, depth)
            self._data[key] = _wrap_value(value, parent, field_path, depth + 1)

    def __getitem__(self, key: str) -> Any:
        """Get item from dictionary."""
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Set item in dictionary.

        Validates field name, wraps nested structures, and marks parent as dirty.

        Args:
            key: Field name.
            value: Value to set.

        Raises:
            FirestoreConstraintError: If field name is invalid or nesting depth exceeds limit.
        """
        validate_field_name(key, self._depth)
        wrapped_value = _wrap_value(value, self._parent, self._field_path, self._depth + 1)
        self._data[key] = wrapped_value
        self._parent._mark_field_dirty(self._field_path)

    def __delitem__(self, key: str) -> None:
        """
        Delete item from dictionary and mark parent as dirty.

        Args:
            key: Field name to delete.
        """
        del self._data[key]
        self._parent._mark_field_dirty(self._field_path)

    def __iter__(self) -> Iterator[str]:
        """Iterate over dictionary keys."""
        return iter(self._data)

    def __len__(self) -> int:
        """Get number of items in dictionary."""
        return len(self._data)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ProxiedMap({self._data!r})"

    # Additional MutableMapping methods that mutate the dict

    def clear(self) -> None:
        """Clear all items and mark parent as dirty."""
        self._data.clear()
        self._parent._mark_field_dirty(self._field_path)

    def pop(self, key: str, *args) -> Any:
        """Remove and return item, marking parent as dirty."""
        result = self._data.pop(key, *args)
        self._parent._mark_field_dirty(self._field_path)
        return _unwrap_value(result)

    def popitem(self) -> tuple[str, Any]:
        """Remove and return arbitrary item, marking parent as dirty."""
        key, value = self._data.popitem()
        self._parent._mark_field_dirty(self._field_path)
        return key, _unwrap_value(value)

    def setdefault(self, key: str, default: Any = None) -> Any:
        """
        Get item or set default, wrapping value and marking parent as dirty if needed.

        Args:
            key: Field name.
            default: Default value if key doesn't exist.

        Returns:
            Existing value or default.

        Raises:
            FirestoreConstraintError: If field name is invalid or nesting depth exceeds limit.
        """
        if key not in self._data:
            validate_field_name(key, self._depth)
            wrapped_default = _wrap_value(default, self._parent, self._field_path, self._depth + 1)
            self._data[key] = wrapped_default
            self._parent._mark_field_dirty(self._field_path)
            return wrapped_default
        return self._data[key]

    def update(self, *args, **kwargs) -> None:
        """
        Update dictionary with items from another dict/iterable, marking parent as dirty.

        Args:
            *args: Dict or iterable of key-value pairs.
            **kwargs: Additional key-value pairs.

        Raises:
            FirestoreConstraintError: If any field name is invalid or nesting depth exceeds limit.
        """
        # Handle both dict and iterable of pairs
        if args:
            other = args[0]
            if isinstance(other, dict):
                items = other.items()
            else:
                items = other
            for key, value in items:
                self[key] = value  # Use __setitem__ for validation and wrapping

        # Handle keyword arguments
        for key, value in kwargs.items():
            self[key] = value  # Use __setitem__ for validation and wrapping

    def __eq__(self, other: Any) -> bool:
        """
        Compare for equality with another ProxiedMap or plain dict.

        Args:
            other: Object to compare with.

        Returns:
            True if equal, False otherwise.
        """
        if isinstance(other, ProxiedMap):
            return self._data == other._data
        elif isinstance(other, dict):
            return self._data == other
        return NotImplemented
