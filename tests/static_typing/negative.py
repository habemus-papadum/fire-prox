"""Static typing fixtures that should fail under strict analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing_extensions import assert_type

from fire_prox import FireCollection, FireObject


@dataclass
class UserProfile:
    display_name: str
    age: int


def incorrect_binding(users: FireCollection[UserProfile]) -> None:
    """Intentional mismatch to ensure schema typing surfaces errors."""
    doc = users.doc("ada")
    assert_type(doc, FireObject[int])


def missing_schema(users: FireCollection[object]) -> None:
    """Using typed annotations without binding should fail."""
    doc = users.doc("ada")
    assert_type(doc, FireObject[UserProfile])
