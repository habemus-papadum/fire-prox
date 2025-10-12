"""
FireVector: Wrapper for Firestore Vector embeddings.

This module provides the FireVector class, which wraps Firestore's native
Vector type with a Pythonic interface for working with vector embeddings.
"""

from typing import List, Union

from google.cloud.firestore_v1.vector import Vector

# Firestore's maximum supported embedding dimension
MAX_DIMENSIONS = 2048


class FireVector:
    """
    A wrapper for Firestore Vector embeddings.

    FireVector provides a Pythonic interface to Firestore's vector embeddings
    with automatic validation, type conversion, and convenient methods for
    working with embedding vectors.

    Firestore vectors are used for similarity search and can store up to 2048
    dimensions. This class handles conversion between Python lists and Firestore's
    native Vector type transparently.

    Usage Examples:
        # Create from list
        embedding = FireVector([0.1, 0.2, 0.3])

        # Store in document
        doc = collection.new()
        doc.text = "Machine learning is fascinating"
        doc.embedding = embedding
        doc.save()

        # Read from document
        retrieved = collection.doc('doc_id')
        retrieved.fetch()
        print(retrieved.embedding.dimensions)  # 3
        print(retrieved.embedding.to_list())   # [0.1, 0.2, 0.3]

    Important Notes:
        - Firestore emulator DOES NOT support vector embeddings
        - Maximum 2048 dimensions (enforced by default)
        - Vectors cannot be nested in arrays or maps
        - Use with production Firestore for full functionality

    Attributes:
        _values: The internal list of float values representing the embedding.
    """

    def __init__(self, values: Union[List[float], tuple], validate: bool = True):
        """
        Initialize a FireVector with embedding values.

        Args:
            values: List or tuple of float values representing the embedding.
            validate: If True, validates dimension limit (default: True).

        Raises:
            TypeError: If values is not a list or tuple, or contains non-numeric values.
            ValueError: If validation is enabled and dimensions exceed 2048.

        Example:
            # Basic creation
            vec = FireVector([0.1, 0.2, 0.3])

            # Create from tuple
            vec = FireVector((0.1, 0.2, 0.3))

            # Skip validation (use with caution)
            vec = FireVector([0.1] * 3000, validate=False)
        """
        if not isinstance(values, (list, tuple)):
            raise TypeError(f"Values must be a list or tuple, got {type(values).__name__}")

        # Convert all values to float and validate they're numeric
        try:
            self._values = [float(v) for v in values]
        except (TypeError, ValueError) as e:
            raise TypeError(f"All values must be numeric: {e}")

        if validate and len(self._values) > MAX_DIMENSIONS:
            raise ValueError(
                f"Vector dimensions ({len(self._values)}) exceed Firestore's "
                f"maximum of {MAX_DIMENSIONS}. Consider using dimensionality "
                f"reduction or set validate=False (not recommended)."
            )

    @property
    def dimensions(self) -> int:
        """
        Get the number of dimensions in this vector.

        Returns:
            The dimension count (length of the embedding vector).

        Example:
            vec = FireVector([0.1, 0.2, 0.3])
            print(vec.dimensions)  # 3
        """
        return len(self._values)

    def to_list(self) -> List[float]:
        """
        Convert the vector to a Python list.

        Returns:
            A list of float values representing the embedding.

        Example:
            vec = FireVector([0.1, 0.2, 0.3])
            values = vec.to_list()
            print(values)  # [0.1, 0.2, 0.3]

            # Use for further processing
            import numpy as np
            arr = np.array(vec.to_list())
        """
        return self._values.copy()

    def to_firestore_vector(self) -> Vector:
        """
        Convert to Firestore's native Vector type.

        This method is used internally by FireProx to convert FireVector
        objects to the native Vector type before storing in Firestore.

        Returns:
            A google.cloud.firestore_v1.vector.Vector instance.

        Example:
            vec = FireVector([0.1, 0.2, 0.3])
            native_vec = vec.to_firestore_vector()
            # Can be used directly with native Firestore API
        """
        return Vector(self._values)

    @classmethod
    def from_firestore_vector(cls, vector: Vector) -> 'FireVector':
        """
        Create a FireVector from Firestore's native Vector type.

        This method is used internally by FireProx when reading vectors from
        Firestore documents.

        Args:
            vector: A google.cloud.firestore_v1.vector.Vector instance.

        Returns:
            A FireVector wrapping the native vector's values.

        Raises:
            TypeError: If vector is not a Vector instance.

        Example:
            # Typically called automatically by FireProx
            from google.cloud.firestore_v1.vector import Vector
            native_vec = Vector([0.1, 0.2, 0.3])
            fire_vec = FireVector.from_firestore_vector(native_vec)
        """
        if not isinstance(vector, Vector):
            raise TypeError(f"Expected Vector instance, got {type(vector).__name__}")

        # Extract values from native Vector
        # Vector.to_map_value() returns {'__type__': '__vector__', 'value': (v1, v2, ...)}
        map_value = vector.to_map_value()
        float_values = list(map_value['value'])

        # Skip validation since it came from Firestore
        return cls(float_values, validate=False)

    def __repr__(self) -> str:
        """
        Return a detailed string representation.

        Returns:
            String showing the class name, dimensions, and first few values.

        Example:
            vec = FireVector([0.1, 0.2, 0.3, 0.4, 0.5])
            print(repr(vec))
            # FireVector(dimensions=5, values=[0.1, 0.2, 0.3, ...])
        """
        if len(self._values) <= 5:
            values_str = str(self._values)
        else:
            preview = self._values[:3]
            values_str = f"{preview[0]:.4f}, {preview[1]:.4f}, {preview[2]:.4f}, ... ({len(self._values)} total)"

        return f"FireVector(dimensions={self.dimensions}, values=[{values_str}])"

    def __str__(self) -> str:
        """
        Return a concise string representation.

        Returns:
            String showing dimensions and value summary.

        Example:
            vec = FireVector([0.1, 0.2, 0.3])
            print(str(vec))  # Vector(3 dimensions)
        """
        return f"Vector({self.dimensions} dimensions)"

    def __eq__(self, other) -> bool:
        """
        Check equality with another FireVector.

        Two FireVectors are equal if they have the same values in the same order.

        Args:
            other: Another FireVector instance.

        Returns:
            True if vectors are equal, False otherwise.

        Example:
            vec1 = FireVector([0.1, 0.2, 0.3])
            vec2 = FireVector([0.1, 0.2, 0.3])
            vec3 = FireVector([0.1, 0.2, 0.4])

            assert vec1 == vec2
            assert vec1 != vec3
        """
        if not isinstance(other, FireVector):
            return False
        return self._values == other._values

    def __len__(self) -> int:
        """
        Get the number of dimensions (same as .dimensions property).

        Returns:
            The dimension count.

        Example:
            vec = FireVector([0.1, 0.2, 0.3])
            print(len(vec))  # 3
        """
        return len(self._values)

    def __getitem__(self, index: int) -> float:
        """
        Access individual dimensions by index.

        Args:
            index: The dimension index (0-based).

        Returns:
            The value at the specified dimension.

        Raises:
            IndexError: If index is out of range.

        Example:
            vec = FireVector([0.1, 0.2, 0.3])
            print(vec[0])  # 0.1
            print(vec[1])  # 0.2
            print(vec[-1]) # 0.3 (last dimension)
        """
        return self._values[index]

    def __iter__(self):
        """
        Iterate over the vector's values.

        Yields:
            Each float value in the vector.

        Example:
            vec = FireVector([0.1, 0.2, 0.3])
            for value in vec:
                print(value)
            # Output: 0.1, 0.2, 0.3
        """
        return iter(self._values)
