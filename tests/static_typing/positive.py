"""Static typing fixtures that should pass without errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from typing_extensions import assert_type

from fire_prox import FireCollection, FireObject


@dataclass
class UserProfile:
    display_name: str
    age: int


def annotate_collection(users: FireCollection[UserProfile]) -> None:
    """Typed collections propagate FireObject generics to documents."""
    doc = users.doc("ada")
    assert_type(doc, FireObject[UserProfile])


def refine_untyped_collection(users: FireCollection[object]) -> None:
    """Binding a schema upgrades the collection's type parameter."""
    typed_users = users.with_schema(UserProfile)
    assert_type(typed_users, FireCollection[UserProfile])
    doc = typed_users.doc("ada")
    assert_type(doc, FireObject[UserProfile])


def round_trip_binding(users: FireCollection[UserProfile]) -> None:
    """Schema metadata survives through intermediate casts."""
    any_collection = cast(FireCollection[object], users)
    rebound = any_collection.with_schema(UserProfile)
    assert_type(rebound, FireCollection[UserProfile])
    assert_type(rebound.doc("ada"), FireObject[UserProfile])
