"""
Unit tests for Phase 3: ProxiedMap, ProxiedList, and constraint validation.

These tests verify the proxy classes and Firestore constraint enforcement
without requiring a Firestore emulator.
"""

import pytest
from unittest.mock import Mock

from fire_prox.proxied_map import ProxiedMap, _wrap_value, _unwrap_value
from fire_prox.proxied_list import ProxiedList
from fire_prox.firestore_constraints import (
    validate_field_name,
    validate_nesting_depth,
    FirestoreConstraintError,
    MAX_NESTING_DEPTH,
    MAX_FIELD_NAME_BYTES,
)


# ============================================================================
# Firestore Constraint Tests
# ============================================================================

class TestFirestoreConstraints:
    """Test Firestore constraint validation."""

    def test_valid_field_name(self):
        """Test that valid field names are accepted."""
        validate_field_name("email")
        validate_field_name("user_name")
        validate_field_name("field123")
        validate_field_name("_private")
        # Should not raise

    def test_invalid_double_underscore_pattern(self):
        """Test that __name__ pattern is rejected."""
        with pytest.raises(FirestoreConstraintError, match="__name__ pattern"):
            validate_field_name("__invalid__")

        with pytest.raises(FirestoreConstraintError, match="__name__ pattern"):
            validate_field_name("__private__")

    def test_empty_field_name(self):
        """Test that empty field names are rejected."""
        with pytest.raises(FirestoreConstraintError, match="cannot be empty"):
            validate_field_name("")

    def test_field_name_with_whitespace(self):
        """Test that field names with leading/trailing whitespace are rejected."""
        with pytest.raises(FirestoreConstraintError, match="whitespace"):
            validate_field_name(" email")

        with pytest.raises(FirestoreConstraintError, match="whitespace"):
            validate_field_name("email ")

        with pytest.raises(FirestoreConstraintError, match="whitespace"):
            validate_field_name(" email ")

    def test_field_name_too_long(self):
        """Test that excessively long field names are rejected."""
        # Create a field name that exceeds MAX_FIELD_NAME_BYTES
        long_name = "a" * (MAX_FIELD_NAME_BYTES + 1)
        with pytest.raises(FirestoreConstraintError, match="exceeds maximum length"):
            validate_field_name(long_name)

    def test_valid_nesting_depth(self):
        """Test that valid nesting depths are accepted."""
        validate_nesting_depth(0)
        validate_nesting_depth(10)
        validate_nesting_depth(MAX_NESTING_DEPTH - 1)
        # Should not raise

    def test_excessive_nesting_depth(self):
        """Test that excessive nesting depth is rejected."""
        with pytest.raises(FirestoreConstraintError, match="nesting depth limit exceeded"):
            validate_nesting_depth(MAX_NESTING_DEPTH)

        with pytest.raises(FirestoreConstraintError, match="nesting depth limit exceeded"):
            validate_nesting_depth(MAX_NESTING_DEPTH + 5)


# ============================================================================
# ProxiedMap Tests
# ============================================================================

class TestProxiedMap:
    """Test ProxiedMap functionality."""

    @pytest.fixture
    def mock_parent(self):
        """Create a mock parent FireObject."""
        parent = Mock()
        parent._mark_field_dirty = Mock()
        return parent

    def test_proxiedmap_creation(self, mock_parent):
        """Test creating a ProxiedMap."""
        data = {'a': 1, 'b': 2}
        proxy = ProxiedMap(data, mock_parent, 'settings', depth=0)

        assert len(proxy) == 2
        assert proxy['a'] == 1
        assert proxy['b'] == 2

    def test_proxiedmap_setitem_marks_dirty(self, mock_parent):
        """Test that setting an item marks parent as dirty."""
        proxy = ProxiedMap({}, mock_parent, 'settings', depth=0)
        proxy['email'] = 'ada@lovelace.com'

        # Parent should be marked dirty
        mock_parent._mark_field_dirty.assert_called_with('settings')
        assert proxy['email'] == 'ada@lovelace.com'

    def test_proxiedmap_delitem_marks_dirty(self, mock_parent):
        """Test that deleting an item marks parent as dirty."""
        proxy = ProxiedMap({'email': 'ada@lovelace.com'}, mock_parent, 'settings', depth=0)
        del proxy['email']

        mock_parent._mark_field_dirty.assert_called_with('settings')
        assert 'email' not in proxy

    def test_proxiedmap_clear_marks_dirty(self, mock_parent):
        """Test that clearing marks parent as dirty."""
        proxy = ProxiedMap({'a': 1, 'b': 2}, mock_parent, 'settings', depth=0)
        proxy.clear()

        mock_parent._mark_field_dirty.assert_called_with('settings')
        assert len(proxy) == 0

    def test_proxiedmap_update_marks_dirty(self, mock_parent):
        """Test that update marks parent as dirty."""
        proxy = ProxiedMap({}, mock_parent, 'settings', depth=0)
        proxy.update({'a': 1, 'b': 2})

        mock_parent._mark_field_dirty.assert_called()
        assert proxy['a'] == 1
        assert proxy['b'] == 2

    def test_proxiedmap_pop_marks_dirty(self, mock_parent):
        """Test that pop marks parent as dirty."""
        proxy = ProxiedMap({'email': 'ada@lovelace.com'}, mock_parent, 'settings', depth=0)
        value = proxy.pop('email')

        assert value == 'ada@lovelace.com'
        mock_parent._mark_field_dirty.assert_called_with('settings')
        assert 'email' not in proxy

    def test_proxiedmap_setdefault_marks_dirty(self, mock_parent):
        """Test that setdefault marks parent as dirty when setting default."""
        proxy = ProxiedMap({}, mock_parent, 'settings', depth=0)
        value = proxy.setdefault('theme', 'dark')

        assert value == 'dark'
        mock_parent._mark_field_dirty.assert_called_with('settings')

    def test_proxiedmap_setdefault_no_dirty_if_exists(self, mock_parent):
        """Test that setdefault doesn't mark dirty if key exists."""
        proxy = ProxiedMap({'theme': 'light'}, mock_parent, 'settings', depth=0)
        mock_parent._mark_field_dirty.reset_mock()

        value = proxy.setdefault('theme', 'dark')

        assert value == 'light'
        mock_parent._mark_field_dirty.assert_not_called()

    def test_proxiedmap_nested_dict_wrapping(self, mock_parent):
        """Test that nested dicts are automatically wrapped."""
        proxy = ProxiedMap({'config': {'theme': 'dark'}}, mock_parent, 'settings', depth=0)

        # Nested dict should be wrapped in ProxiedMap
        nested = proxy['config']
        assert isinstance(nested, ProxiedMap)
        assert nested['theme'] == 'dark'

    def test_proxiedmap_nested_list_wrapping(self, mock_parent):
        """Test that nested lists are automatically wrapped."""
        proxy = ProxiedMap({'tags': ['python', 'firestore']}, mock_parent, 'data', depth=0)

        # Nested list should be wrapped in ProxiedList
        nested = proxy['tags']
        assert isinstance(nested, ProxiedList)
        assert len(nested) == 2

    def test_proxiedmap_invalid_field_name(self, mock_parent):
        """Test that invalid field names are rejected."""
        proxy = ProxiedMap({}, mock_parent, 'settings', depth=0)

        with pytest.raises(FirestoreConstraintError):
            proxy['__invalid__'] = 'value'

    def test_proxiedmap_iteration(self, mock_parent):
        """Test that iteration works correctly."""
        data = {'a': 1, 'b': 2, 'c': 3}
        proxy = ProxiedMap(data, mock_parent, 'data', depth=0)

        keys = list(proxy.keys())
        assert set(keys) == {'a', 'b', 'c'}

        values = list(proxy.values())
        assert set(values) == {1, 2, 3}


# ============================================================================
# ProxiedList Tests
# ============================================================================

class TestProxiedList:
    """Test ProxiedList functionality."""

    @pytest.fixture
    def mock_parent(self):
        """Create a mock parent FireObject."""
        parent = Mock()
        parent._mark_field_dirty = Mock()
        return parent

    def test_proxiedlist_creation(self, mock_parent):
        """Test creating a ProxiedList."""
        data = [1, 2, 3]
        proxy = ProxiedList(data, mock_parent, 'tags', depth=0)

        assert len(proxy) == 3
        assert proxy[0] == 1
        assert proxy[1] == 2
        assert proxy[2] == 3

    def test_proxiedlist_append_marks_dirty(self, mock_parent):
        """Test that append marks parent as dirty."""
        proxy = ProxiedList([], mock_parent, 'tags', depth=0)
        proxy.append('python')

        mock_parent._mark_field_dirty.assert_called_with('tags')
        assert proxy[0] == 'python'

    def test_proxiedlist_extend_marks_dirty(self, mock_parent):
        """Test that extend marks parent as dirty."""
        proxy = ProxiedList(['python'], mock_parent, 'tags', depth=0)
        proxy.extend(['firestore', 'gcp'])

        mock_parent._mark_field_dirty.assert_called_with('tags')
        assert len(proxy) == 3

    def test_proxiedlist_setitem_marks_dirty(self, mock_parent):
        """Test that setting an item marks parent as dirty."""
        proxy = ProxiedList(['old'], mock_parent, 'tags', depth=0)
        proxy[0] = 'new'

        mock_parent._mark_field_dirty.assert_called_with('tags')
        assert proxy[0] == 'new'

    def test_proxiedlist_delitem_marks_dirty(self, mock_parent):
        """Test that deleting an item marks parent as dirty."""
        proxy = ProxiedList([1, 2, 3], mock_parent, 'numbers', depth=0)
        del proxy[1]

        mock_parent._mark_field_dirty.assert_called_with('numbers')
        assert len(proxy) == 2
        assert proxy[0] == 1
        assert proxy[1] == 3

    def test_proxiedlist_insert_marks_dirty(self, mock_parent):
        """Test that insert marks parent as dirty."""
        proxy = ProxiedList([1, 3], mock_parent, 'numbers', depth=0)
        proxy.insert(1, 2)

        mock_parent._mark_field_dirty.assert_called_with('numbers')
        assert proxy[1] == 2

    def test_proxiedlist_pop_marks_dirty(self, mock_parent):
        """Test that pop marks parent as dirty."""
        proxy = ProxiedList([1, 2, 3], mock_parent, 'numbers', depth=0)
        value = proxy.pop()

        assert value == 3
        mock_parent._mark_field_dirty.assert_called_with('numbers')
        assert len(proxy) == 2

    def test_proxiedlist_remove_marks_dirty(self, mock_parent):
        """Test that remove marks parent as dirty."""
        proxy = ProxiedList([1, 2, 3, 2], mock_parent, 'numbers', depth=0)
        proxy.remove(2)

        mock_parent._mark_field_dirty.assert_called_with('numbers')
        assert list(proxy) == [1, 3, 2]

    def test_proxiedlist_clear_marks_dirty(self, mock_parent):
        """Test that clear marks parent as dirty."""
        proxy = ProxiedList([1, 2, 3], mock_parent, 'numbers', depth=0)
        proxy.clear()

        mock_parent._mark_field_dirty.assert_called_with('numbers')
        assert len(proxy) == 0

    def test_proxiedlist_reverse_marks_dirty(self, mock_parent):
        """Test that reverse marks parent as dirty."""
        proxy = ProxiedList([1, 2, 3], mock_parent, 'numbers', depth=0)
        proxy.reverse()

        mock_parent._mark_field_dirty.assert_called_with('numbers')
        assert list(proxy) == [3, 2, 1]

    def test_proxiedlist_sort_marks_dirty(self, mock_parent):
        """Test that sort marks parent as dirty."""
        proxy = ProxiedList([3, 1, 2], mock_parent, 'numbers', depth=0)
        proxy.sort()

        mock_parent._mark_field_dirty.assert_called_with('numbers')
        assert list(proxy) == [1, 2, 3]

    def test_proxiedlist_nested_dict_wrapping(self, mock_parent):
        """Test that nested dicts are automatically wrapped."""
        proxy = ProxiedList([{'name': 'Ada'}], mock_parent, 'users', depth=0)

        # Nested dict should be wrapped in ProxiedMap
        nested = proxy[0]
        assert isinstance(nested, ProxiedMap)
        assert nested['name'] == 'Ada'

    def test_proxiedlist_nested_list_wrapping(self, mock_parent):
        """Test that nested lists are automatically wrapped."""
        proxy = ProxiedList([[1, 2], [3, 4]], mock_parent, 'matrix', depth=0)

        # Nested list should be wrapped in ProxiedList
        nested = proxy[0]
        assert isinstance(nested, ProxiedList)
        assert len(nested) == 2

    def test_proxiedlist_slice_assignment(self, mock_parent):
        """Test that slice assignment works and marks dirty."""
        proxy = ProxiedList([1, 2, 3, 4, 5], mock_parent, 'numbers', depth=0)
        proxy[1:3] = [10, 20]

        mock_parent._mark_field_dirty.assert_called_with('numbers')
        assert list(proxy) == [1, 10, 20, 4, 5]


# ============================================================================
# Wrap/Unwrap Tests
# ============================================================================

class TestWrapUnwrap:
    """Test wrapping and unwrapping of values."""

    @pytest.fixture
    def mock_parent(self):
        """Create a mock parent FireObject."""
        parent = Mock()
        parent._mark_field_dirty = Mock()
        return parent

    def test_wrap_dict(self, mock_parent):
        """Test wrapping a dictionary."""
        value = {'a': 1, 'b': 2}
        wrapped = _wrap_value(value, mock_parent, 'data', depth=0)

        assert isinstance(wrapped, ProxiedMap)
        assert wrapped['a'] == 1

    def test_wrap_list(self, mock_parent):
        """Test wrapping a list."""
        value = [1, 2, 3]
        wrapped = _wrap_value(value, mock_parent, 'data', depth=0)

        assert isinstance(wrapped, ProxiedList)
        assert wrapped[0] == 1

    def test_wrap_primitives(self, mock_parent):
        """Test that primitives are not wrapped."""
        assert _wrap_value(42, mock_parent, 'num', depth=0) == 42
        assert _wrap_value('hello', mock_parent, 'str', depth=0) == 'hello'
        assert _wrap_value(True, mock_parent, 'bool', depth=0) is True
        assert _wrap_value(None, mock_parent, 'none', depth=0) is None

    def test_wrap_nested_structures(self, mock_parent):
        """Test wrapping deeply nested structures."""
        value = {
            'config': {
                'theme': 'dark',
                'tags': ['python', 'firestore'],
            },
            'scores': [1, 2, 3],
        }
        wrapped = _wrap_value(value, mock_parent, 'data', depth=0)

        assert isinstance(wrapped, ProxiedMap)
        assert isinstance(wrapped['config'], ProxiedMap)
        assert isinstance(wrapped['config']['tags'], ProxiedList)
        assert isinstance(wrapped['scores'], ProxiedList)

    def test_unwrap_proxiedmap(self, mock_parent):
        """Test unwrapping a ProxiedMap."""
        proxy = ProxiedMap({'a': 1, 'b': 2}, mock_parent, 'data', depth=0)
        unwrapped = _unwrap_value(proxy)

        assert isinstance(unwrapped, dict)
        assert unwrapped == {'a': 1, 'b': 2}

    def test_unwrap_proxiedlist(self, mock_parent):
        """Test unwrapping a ProxiedList."""
        proxy = ProxiedList([1, 2, 3], mock_parent, 'data', depth=0)
        unwrapped = _unwrap_value(proxy)

        assert isinstance(unwrapped, list)
        assert unwrapped == [1, 2, 3]

    def test_unwrap_primitives(self):
        """Test that primitives are not modified during unwrap."""
        assert _unwrap_value(42) == 42
        assert _unwrap_value('hello') == 'hello'
        assert _unwrap_value(True) is True
        assert _unwrap_value(None) is None

    def test_unwrap_nested_structures(self, mock_parent):
        """Test unwrapping deeply nested structures."""
        proxy = ProxiedMap({
            'config': ProxiedMap({'theme': 'dark'}, mock_parent, 'data.config', depth=1),
            'tags': ProxiedList(['python'], mock_parent, 'data.tags', depth=1),
        }, mock_parent, 'data', depth=0)

        unwrapped = _unwrap_value(proxy)

        assert isinstance(unwrapped, dict)
        assert isinstance(unwrapped['config'], dict)
        assert isinstance(unwrapped['tags'], list)
        assert unwrapped == {
            'config': {'theme': 'dark'},
            'tags': ['python'],
        }

    def test_wrap_excessive_depth(self, mock_parent):
        """Test that wrapping at excessive depth raises error."""
        value = {'nested': 'value'}  # Single level of nesting

        # Should work at depth 19 (within limit: 19 -> 20 for nested key)
        # But value at depth 19 means nested value at depth 20, which exceeds limit
        # So we test at depth 18 instead (18 -> 19 for nested key)
        wrapped = _wrap_value(value, mock_parent, 'data', depth=18)
        assert isinstance(wrapped, ProxiedMap)

        # Should fail at depth 19 (19 -> 20 for nested key, exceeds limit)
        with pytest.raises(FirestoreConstraintError, match="nesting depth limit exceeded"):
            _wrap_value(value, mock_parent, 'data', depth=19)
