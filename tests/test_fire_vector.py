"""
Unit tests for FireVector class.

These tests do not require Firestore and test the FireVector wrapper logic.
"""

import pytest
from src.fire_prox.fire_vector import FireVector, MAX_DIMENSIONS
from google.cloud.firestore_v1.vector import Vector


class TestFireVectorCreation:
    """Test FireVector object creation."""

    def test_create_from_list(self):
        """Test creating FireVector from a list."""
        values = [0.1, 0.2, 0.3]
        vec = FireVector(values)

        assert vec.dimensions == 3
        assert vec.to_list() == values

    def test_create_from_tuple(self):
        """Test creating FireVector from a tuple."""
        values = (0.1, 0.2, 0.3)
        vec = FireVector(values)

        assert vec.dimensions == 3
        assert vec.to_list() == [0.1, 0.2, 0.3]

    def test_create_with_integers(self):
        """Test that integer values are converted to floats."""
        values = [1, 2, 3]
        vec = FireVector(values)

        assert vec.to_list() == [1.0, 2.0, 3.0]
        assert all(isinstance(v, float) for v in vec.to_list())

    def test_create_empty_vector(self):
        """Test creating an empty vector."""
        vec = FireVector([])

        assert vec.dimensions == 0
        assert vec.to_list() == []

    def test_create_large_valid_vector(self):
        """Test creating a vector at the dimension limit."""
        values = [0.1] * MAX_DIMENSIONS
        vec = FireVector(values)

        assert vec.dimensions == MAX_DIMENSIONS

    def test_invalid_type_raises_error(self):
        """Test that non-list/tuple types raise TypeError."""
        with pytest.raises(TypeError, match="must be a list or tuple"):
            FireVector("not a list")

        with pytest.raises(TypeError, match="must be a list or tuple"):
            FireVector(123)

        with pytest.raises(TypeError, match="must be a list or tuple"):
            FireVector({1: 0.1})

    def test_non_numeric_values_raise_error(self):
        """Test that non-numeric values raise TypeError."""
        with pytest.raises(TypeError, match="All values must be numeric"):
            FireVector([0.1, "invalid", 0.3])

        with pytest.raises(TypeError, match="All values must be numeric"):
            FireVector([0.1, None, 0.3])


class TestFireVectorValidation:
    """Test dimension validation."""

    def test_exceeds_max_dimensions_with_validation(self):
        """Test that exceeding max dimensions raises ValueError."""
        values = [0.1] * (MAX_DIMENSIONS + 1)

        with pytest.raises(ValueError, match=f"exceed Firestore's maximum of {MAX_DIMENSIONS}"):
            FireVector(values)

    def test_exceeds_max_dimensions_without_validation(self):
        """Test that validation can be disabled."""
        values = [0.1] * (MAX_DIMENSIONS + 100)
        vec = FireVector(values, validate=False)

        assert vec.dimensions == MAX_DIMENSIONS + 100
        assert len(vec.to_list()) == MAX_DIMENSIONS + 100


class TestFireVectorConversion:
    """Test conversion methods."""

    def test_to_list_returns_copy(self):
        """Test that to_list() returns a copy, not a reference."""
        vec = FireVector([0.1, 0.2, 0.3])
        list1 = vec.to_list()
        list2 = vec.to_list()

        # Modify list1
        list1[0] = 999.0

        # list2 and original should be unchanged
        assert list2[0] == 0.1
        assert vec[0] == 0.1

    def test_to_firestore_vector(self):
        """Test conversion to native Firestore Vector."""
        values = [0.1, 0.2, 0.3]
        fire_vec = FireVector(values)
        native_vec = fire_vec.to_firestore_vector()

        assert isinstance(native_vec, Vector)
        # Native Vector should contain our values
        # (actual verification would need Firestore)

    def test_from_firestore_vector(self):
        """Test creating FireVector from native Vector."""
        # Create a native Vector
        native_vec = Vector([0.1, 0.2, 0.3])

        # Convert to FireVector
        fire_vec = FireVector.from_firestore_vector(native_vec)

        assert isinstance(fire_vec, FireVector)
        assert fire_vec.dimensions == 3
        # Values should match (approximately due to float precision)
        result = fire_vec.to_list()
        assert len(result) == 3
        assert all(isinstance(v, float) for v in result)

    def test_from_firestore_vector_invalid_type(self):
        """Test that from_firestore_vector requires Vector type."""
        with pytest.raises(TypeError, match="Expected Vector instance"):
            FireVector.from_firestore_vector([0.1, 0.2, 0.3])

        with pytest.raises(TypeError, match="Expected Vector instance"):
            FireVector.from_firestore_vector("not a vector")


class TestFireVectorProperties:
    """Test FireVector properties and attributes."""

    def test_dimensions_property(self):
        """Test the dimensions property."""
        vec1 = FireVector([0.1])
        vec2 = FireVector([0.1, 0.2])
        vec3 = FireVector([0.1, 0.2, 0.3])

        assert vec1.dimensions == 1
        assert vec2.dimensions == 2
        assert vec3.dimensions == 3

    def test_len_method(self):
        """Test __len__ method."""
        vec = FireVector([0.1, 0.2, 0.3])

        assert len(vec) == 3
        assert len(vec) == vec.dimensions

    def test_getitem_access(self):
        """Test accessing individual dimensions via indexing."""
        vec = FireVector([0.1, 0.2, 0.3])

        assert vec[0] == 0.1
        assert vec[1] == 0.2
        assert vec[2] == 0.3
        assert vec[-1] == 0.3  # Negative indexing

    def test_getitem_out_of_range(self):
        """Test that out-of-range index raises IndexError."""
        vec = FireVector([0.1, 0.2, 0.3])

        with pytest.raises(IndexError):
            _ = vec[10]

    def test_iteration(self):
        """Test iterating over vector values."""
        values = [0.1, 0.2, 0.3]
        vec = FireVector(values)

        result = [v for v in vec]
        assert result == values

        # Test with for loop
        collected = []
        for v in vec:
            collected.append(v)
        assert collected == values


class TestFireVectorEquality:
    """Test FireVector equality comparison."""

    def test_equal_vectors(self):
        """Test that vectors with same values are equal."""
        vec1 = FireVector([0.1, 0.2, 0.3])
        vec2 = FireVector([0.1, 0.2, 0.3])

        assert vec1 == vec2

    def test_unequal_vectors(self):
        """Test that vectors with different values are not equal."""
        vec1 = FireVector([0.1, 0.2, 0.3])
        vec2 = FireVector([0.1, 0.2, 0.4])

        assert vec1 != vec2

    def test_different_dimensions(self):
        """Test that vectors with different dimensions are not equal."""
        vec1 = FireVector([0.1, 0.2])
        vec2 = FireVector([0.1, 0.2, 0.3])

        assert vec1 != vec2

    def test_equality_with_non_vector(self):
        """Test equality with non-FireVector types."""
        vec = FireVector([0.1, 0.2, 0.3])

        assert vec != [0.1, 0.2, 0.3]
        assert vec != "not a vector"
        assert vec != 123


class TestFireVectorStringRepresentation:
    """Test string representation methods."""

    def test_str_short_vector(self):
        """Test __str__ for short vectors."""
        vec = FireVector([0.1, 0.2, 0.3])
        result = str(vec)

        assert "Vector" in result
        assert "3 dimensions" in result

    def test_repr_short_vector(self):
        """Test __repr__ for short vectors (≤5 dimensions)."""
        vec = FireVector([0.1, 0.2, 0.3])
        result = repr(vec)

        assert "FireVector" in result
        assert "dimensions=3" in result
        assert "0.1" in result
        assert "0.2" in result
        assert "0.3" in result

    def test_repr_long_vector(self):
        """Test __repr__ for long vectors (>5 dimensions)."""
        vec = FireVector([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7])
        result = repr(vec)

        assert "FireVector" in result
        assert "dimensions=7" in result
        assert "..." in result  # Should show truncation
        assert "7 total" in result


class TestFireVectorEdgeCases:
    """Test edge cases and special scenarios."""

    def test_single_dimension_vector(self):
        """Test vector with a single dimension."""
        vec = FireVector([0.5])

        assert vec.dimensions == 1
        assert vec[0] == 0.5
        assert vec.to_list() == [0.5]

    def test_negative_values(self):
        """Test vector with negative values."""
        vec = FireVector([-0.1, -0.2, 0.3])

        assert vec[0] == -0.1
        assert vec[1] == -0.2
        assert vec[2] == 0.3

    def test_zero_values(self):
        """Test vector with zero values."""
        vec = FireVector([0.0, 0.0, 0.0])

        assert all(v == 0.0 for v in vec)

    def test_very_small_values(self):
        """Test vector with very small float values."""
        vec = FireVector([1e-10, 1e-20, 1e-30])

        assert vec.dimensions == 3
        assert vec[0] == 1e-10

    def test_very_large_values(self):
        """Test vector with very large float values."""
        vec = FireVector([1e10, 1e20, 1e30])

        assert vec.dimensions == 3
        assert vec[0] == 1e10

    def test_mixed_precision_values(self):
        """Test vector with values of different precisions."""
        vec = FireVector([0.1, 0.123456789, 1.0])

        assert vec.dimensions == 3
        result = vec.to_list()
        assert result[1] == 0.123456789
