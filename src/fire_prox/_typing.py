"""Shared typing helpers for schema-aware generics."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TypeVar


# Covariant schema type used across the Fire-Prox surface area. When no schema
# is supplied consumers can continue to treat the API as ``Any``/dynamic, which
# mirrors the library's historical behavior.
SchemaT_co = TypeVar("SchemaT_co", bound=object, covariant=True)

# Invariant schema type for helper APIs that need to accept the same type for
# input and output (e.g., ``with_schema``).
SchemaT = TypeVar("SchemaT", bound=object)

# Convenience alias for schema classes to improve readability in annotations.
SchemaType = type[SchemaT]

