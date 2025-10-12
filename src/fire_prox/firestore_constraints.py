"""
Firestore constraint validation.

This module provides validation functions to enforce Firestore's data structure
constraints at assignment time, providing fail-fast error detection rather than
waiting for runtime failures during save operations.

Firestore Constraints:
- Maximum nesting depth: 20 levels for maps
- Field name restrictions:
  - Cannot use __name__ pattern (double underscores)
  - Cannot have leading or trailing whitespace
  - Maximum length: 1500 bytes (UTF-8 encoded)
  - Cannot be empty string

References:
- https://firebase.google.com/docs/firestore/quotas
"""

# Firestore limits
MAX_NESTING_DEPTH = 20
MAX_FIELD_NAME_BYTES = 1500


class FirestoreConstraintError(ValueError):
    """Raised when a Firestore constraint is violated."""
    pass


def validate_nesting_depth(depth: int, context: str = "") -> None:
    """
    Validate that nesting depth doesn't exceed Firestore's limit.

    Args:
        depth: Current nesting depth (0-indexed).
        context: Optional context string for error message.

    Raises:
        FirestoreConstraintError: If depth exceeds MAX_NESTING_DEPTH.

    Example:
        validate_nesting_depth(19)  # OK
        validate_nesting_depth(20)  # Raises error
    """
    if depth >= MAX_NESTING_DEPTH:
        ctx = f" {context}" if context else ""
        raise FirestoreConstraintError(
            f"Firestore nesting depth limit exceeded{ctx}. "
            f"Maximum depth is {MAX_NESTING_DEPTH} levels, attempted {depth + 1}. "
            "Consider flattening your data structure or using subcollections."
        )


def validate_field_name(name: str, depth: int = 0) -> None:
    """
    Validate that a field name meets Firestore's requirements.

    Args:
        name: Field name to validate.
        depth: Current nesting depth (for error context).

    Raises:
        FirestoreConstraintError: If field name is invalid.

    Example:
        validate_field_name("email")  # OK
        validate_field_name("__private__")  # Raises error
        validate_field_name(" spaces ")  # Raises error
        validate_field_name("")  # Raises error
    """
    # Empty field names not allowed
    if not name:
        raise FirestoreConstraintError(
            f"Field name cannot be empty (at depth {depth})"
        )

    # Check for __name__ pattern
    if name.startswith("__") and name.endswith("__"):
        raise FirestoreConstraintError(
            f"Field name '{name}' cannot match __name__ pattern (at depth {depth}). "
            "Firestore reserves double-underscore names for internal use."
        )

    # Check for leading/trailing whitespace
    if name != name.strip():
        raise FirestoreConstraintError(
            f"Field name '{name}' cannot have leading or trailing whitespace (at depth {depth})"
        )

    # Check byte length (UTF-8 encoding)
    name_bytes = name.encode('utf-8')
    if len(name_bytes) > MAX_FIELD_NAME_BYTES:
        raise FirestoreConstraintError(
            f"Field name '{name}' exceeds maximum length of {MAX_FIELD_NAME_BYTES} bytes "
            f"({len(name_bytes)} bytes, at depth {depth})"
        )
