"""
Comprehensive unit tests for the State enum.

Tests verify that the State enum correctly represents the four possible states
of a FireObject and provides appropriate string representations.
"""

import pytest
from fire_prox.state import State


class TestStateEnum:
    """Test suite for the State enum."""

    def test_state_enum_has_all_required_values(self):
        """Test that State enum has all four required state values."""
        # Verify all four states exist
        assert hasattr(State, 'DETACHED')
        assert hasattr(State, 'ATTACHED')
        assert hasattr(State, 'LOADED')
        assert hasattr(State, 'DELETED')

    def test_state_enum_values_are_unique(self):
        """Test that each State enum value is unique."""
        states = [State.DETACHED, State.ATTACHED, State.LOADED, State.DELETED]
        assert len(states) == len(set(states)), "State values should be unique"

    def test_state_detached_value(self):
        """Test that DETACHED state has correct value."""
        assert State.DETACHED is not None
        assert isinstance(State.DETACHED, State)

    def test_state_attached_value(self):
        """Test that ATTACHED state has correct value."""
        assert State.ATTACHED is not None
        assert isinstance(State.ATTACHED, State)

    def test_state_loaded_value(self):
        """Test that LOADED state has correct value."""
        assert State.LOADED is not None
        assert isinstance(State.LOADED, State)

    def test_state_deleted_value(self):
        """Test that DELETED state has correct value."""
        assert State.DELETED is not None
        assert isinstance(State.DELETED, State)

    def test_state_str_representation(self):
        """Test that State enum provides human-readable string representation."""
        assert str(State.DETACHED) == 'DETACHED'
        assert str(State.ATTACHED) == 'ATTACHED'
        assert str(State.LOADED) == 'LOADED'
        assert str(State.DELETED) == 'DELETED'

    def test_state_repr_representation(self):
        """Test that State enum provides detailed repr representation."""
        assert repr(State.DETACHED) == 'State.DETACHED'
        assert repr(State.ATTACHED) == 'State.ATTACHED'
        assert repr(State.LOADED) == 'State.LOADED'
        assert repr(State.DELETED) == 'State.DELETED'

    def test_state_equality(self):
        """Test that State enum values can be compared for equality."""
        assert State.DETACHED == State.DETACHED
        assert State.ATTACHED == State.ATTACHED
        assert State.LOADED == State.LOADED
        assert State.DELETED == State.DELETED

    def test_state_inequality(self):
        """Test that different State enum values are not equal."""
        assert State.DETACHED != State.ATTACHED
        assert State.DETACHED != State.LOADED
        assert State.DETACHED != State.DELETED
        assert State.ATTACHED != State.LOADED
        assert State.ATTACHED != State.DELETED
        assert State.LOADED != State.DELETED

    def test_state_can_be_used_in_conditionals(self):
        """Test that State enum values work in conditional statements."""
        current_state = State.LOADED

        if current_state == State.LOADED:
            result = "loaded"
        elif current_state == State.ATTACHED:
            result = "attached"
        elif current_state == State.DETACHED:
            result = "detached"
        else:
            result = "deleted"

        assert result == "loaded"

    def test_state_can_be_used_in_dictionaries(self):
        """Test that State enum values can be used as dictionary keys."""
        state_handlers = {
            State.DETACHED: "handle_detached",
            State.ATTACHED: "handle_attached",
            State.LOADED: "handle_loaded",
            State.DELETED: "handle_deleted",
        }

        assert state_handlers[State.LOADED] == "handle_loaded"
        assert len(state_handlers) == 4

    def test_state_iteration(self):
        """Test that State enum can be iterated over."""
        states = list(State)
        assert len(states) == 4
        assert State.DETACHED in states
        assert State.ATTACHED in states
        assert State.LOADED in states
        assert State.DELETED in states

    def test_state_name_property(self):
        """Test that State enum values have correct name property."""
        assert State.DETACHED.name == 'DETACHED'
        assert State.ATTACHED.name == 'ATTACHED'
        assert State.LOADED.name == 'LOADED'
        assert State.DELETED.name == 'DELETED'

    def test_state_value_property(self):
        """Test that State enum values have integer value property."""
        # Values should be unique integers due to auto()
        assert isinstance(State.DETACHED.value, int)
        assert isinstance(State.ATTACHED.value, int)
        assert isinstance(State.LOADED.value, int)
        assert isinstance(State.DELETED.value, int)

        # Values should be distinct
        values = [s.value for s in State]
        assert len(values) == len(set(values))

    def test_state_ordering_reflects_lifecycle(self):
        """Test that State enum values are ordered according to lifecycle."""
        # DETACHED should come first (initial state)
        # ATTACHED and LOADED follow
        # DELETED is terminal state
        assert State.DETACHED.value < State.ATTACHED.value
        assert State.ATTACHED.value < State.LOADED.value
        assert State.LOADED.value < State.DELETED.value


class TestStateDocumentation:
    """Test that State enum has proper documentation."""

    def test_state_module_has_docstring(self):
        """Test that the state module has documentation."""
        from fire_prox import state
        assert state.__doc__ is not None
        assert len(state.__doc__) > 0

    def test_state_enum_has_docstring(self):
        """Test that the State enum class has documentation."""
        assert State.__doc__ is not None
        assert 'state machine' in State.__doc__.lower() or 'lifecycle' in State.__doc__.lower()

    def test_state_values_are_documented(self):
        """Test that individual state values are documented in class docstring."""
        doc = State.__doc__.lower()
        assert 'detached' in doc
        assert 'attached' in doc
        assert 'loaded' in doc
        assert 'deleted' in doc
