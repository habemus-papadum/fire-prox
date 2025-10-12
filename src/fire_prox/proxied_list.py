"""
ProxiedList: List proxy with mutation tracking.

This module implements a transparent proxy for lists that tracks mutations
and reports them to parent FireObject instances. When any element is modified,
the entire top-level field is marked as dirty for conservative saving.

Phase 3 feature.
"""

from collections.abc import MutableSequence
from typing import Any, Iterator, Optional, Union, TYPE_CHECKING

from .firestore_constraints import (
    validate_nesting_depth,
    FirestoreConstraintError
)

if TYPE_CHECKING:
    from .base_fire_object import BaseFireObject


class ProxiedList(MutableSequence):
    """
    List proxy that tracks mutations and enforces Firestore constraints.

    This class wraps a list and transparently tracks any modifications,
    reporting them to the parent FireObject. All nested dictionaries and lists
    are recursively wrapped in proxies.

    When any mutation occurs (append, extend, setitem, etc.), the top-level field
    is marked as dirty in the parent FireObject, causing the entire structure to be
    saved on the next save() call.

    Phase 3 feature.

    Example:
        user = db.doc('users/ada')
        user.tags = ['python', 'math']
        user.save()

        # Mutation automatically tracked
        user.tags.append('computer-science')
        # user is now dirty, will save entire 'tags' field

    Attributes:
        _data: Internal list storage.
        _parent: Parent FireObject that owns this data.
        _field_path: Top-level field path (e.g., 'tags').
        _depth: Current nesting depth (for constraint validation).
    """

    def __init__(
        self,
        data: list,
        parent: 'BaseFireObject',
        field_path: str,
        depth: int = 0
    ):
        """
        Initialize ProxiedList.

        Args:
            data: List to wrap.
            parent: Parent FireObject instance.
            field_path: Field path from root object (top-level field name).
            depth: Current nesting depth (0-indexed).

        Raises:
            FirestoreConstraintError: If nesting depth exceeds limit.
        """
        self._data = []
        self._parent = parent
        self._field_path = field_path
        self._depth = depth

        # Import wrap function (avoiding circular import)
        from .proxied_map import _wrap_value

        # Recursively wrap initial data
        for item in data:
            wrapped_item = _wrap_value(item, parent, field_path, depth + 1)
            self._data.append(wrapped_item)

    def __getitem__(self, index: Union[int, slice]) -> Any:
        """Get item(s) from list."""
        return self._data[index]

    def __setitem__(self, index: Union[int, slice], value: Any) -> None:
        """
        Set item(s) in list, wrapping nested structures and marking parent as dirty.

        Args:
            index: Index or slice.
            value: Value to set (or iterable of values for slice assignment).

        Raises:
            FirestoreConstraintError: If nesting depth exceeds limit.
        """
        # Import wrap function (avoiding circular import)
        from .proxied_map import _wrap_value

        if isinstance(index, slice):
            # Handle slice assignment
            wrapped_values = [_wrap_value(v, self._parent, self._field_path, self._depth + 1)
                            for v in value]
            self._data[index] = wrapped_values
        else:
            # Handle single item assignment
            wrapped_value = _wrap_value(value, self._parent, self._field_path, self._depth + 1)
            self._data[index] = wrapped_value

        self._parent._mark_field_dirty(self._field_path)

    def __delitem__(self, index: Union[int, slice]) -> None:
        """
        Delete item(s) from list and mark parent as dirty.

        Args:
            index: Index or slice.
        """
        del self._data[index]
        self._parent._mark_field_dirty(self._field_path)

    def __len__(self) -> int:
        """Get number of items in list."""
        return len(self._data)

    def insert(self, index: int, value: Any) -> None:
        """
        Insert item at index, wrapping nested structures and marking parent as dirty.

        Args:
            index: Index to insert at.
            value: Value to insert.

        Raises:
            FirestoreConstraintError: If nesting depth exceeds limit.
        """
        # Import wrap function (avoiding circular import)
        from .proxied_map import _wrap_value

        wrapped_value = _wrap_value(value, self._parent, self._field_path, self._depth + 1)
        self._data.insert(index, wrapped_value)
        self._parent._mark_field_dirty(self._field_path)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ProxiedList({self._data!r})"

    # Additional MutableSequence methods

    def append(self, value: Any) -> None:
        """
        Append item to list, wrapping nested structures and marking parent as dirty.

        Args:
            value: Value to append.

        Raises:
            FirestoreConstraintError: If nesting depth exceeds limit.
        """
        # Import wrap function (avoiding circular import)
        from .proxied_map import _wrap_value

        wrapped_value = _wrap_value(value, self._parent, self._field_path, self._depth + 1)
        self._data.append(wrapped_value)
        self._parent._mark_field_dirty(self._field_path)

    def extend(self, values: list) -> None:
        """
        Extend list with items, wrapping nested structures and marking parent as dirty.

        Args:
            values: Iterable of values to append.

        Raises:
            FirestoreConstraintError: If nesting depth exceeds limit.
        """
        # Import wrap function (avoiding circular import)
        from .proxied_map import _wrap_value

        wrapped_values = [_wrap_value(v, self._parent, self._field_path, self._depth + 1)
                         for v in values]
        self._data.extend(wrapped_values)
        self._parent._mark_field_dirty(self._field_path)

    def pop(self, index: int = -1) -> Any:
        """
        Remove and return item at index, marking parent as dirty.

        Args:
            index: Index to pop (default: -1, last item).

        Returns:
            Unwrapped value that was removed.
        """
        # Import unwrap function (avoiding circular import)
        from .proxied_map import _unwrap_value

        result = self._data.pop(index)
        self._parent._mark_field_dirty(self._field_path)
        return _unwrap_value(result)

    def remove(self, value: Any) -> None:
        """
        Remove first occurrence of value, marking parent as dirty.

        Args:
            value: Value to remove.

        Raises:
            ValueError: If value is not in list.
        """
        self._data.remove(value)
        self._parent._mark_field_dirty(self._field_path)

    def clear(self) -> None:
        """Clear all items and mark parent as dirty."""
        self._data.clear()
        self._parent._mark_field_dirty(self._field_path)

    def reverse(self) -> None:
        """Reverse list in-place and mark parent as dirty."""
        self._data.reverse()
        self._parent._mark_field_dirty(self._field_path)

    def sort(self, *args, **kwargs) -> None:
        """
        Sort list in-place and mark parent as dirty.

        Args:
            *args: Positional arguments for sort (key, reverse).
            **kwargs: Keyword arguments for sort.
        """
        self._data.sort(*args, **kwargs)
        self._parent._mark_field_dirty(self._field_path)

    def __eq__(self, other: Any) -> bool:
        """
        Compare for equality with another ProxiedList or plain list.

        Args:
            other: Object to compare with.

        Returns:
            True if equal, False otherwise.
        """
        if isinstance(other, ProxiedList):
            return self._data == other._data
        elif isinstance(other, list):
            return self._data == other
        return NotImplemented
