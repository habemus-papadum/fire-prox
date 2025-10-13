"""Static typing fixtures that should pass without errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from typing_extensions import assert_type

from fire_prox import (
    AsyncFireObject,
    AsyncFireCollection,
    AsyncFireProx,
    FireCollection,
    FireObject,
    FireProx,
)


@dataclass
class UserProfile:
    display_name: str
    age: int


@dataclass
class Order:
    purchaser: FireObject[UserProfile]
    total: float


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


def direct_binding(db: FireProx) -> None:
    """Binding during collection creation returns typed collections."""
    users = db.collection("users", UserProfile)
    assert_type(users, FireCollection[UserProfile])
    ada = users.doc("ada")
    assert_type(ada, FireObject[UserProfile])


async def async_direct_binding(db: AsyncFireProx) -> None:
    """Async collections accept inline schema hints as well."""
    users = db.collection("users", UserProfile)
    assert_type(users, AsyncFireCollection[UserProfile])
    ada = users.doc("ada")
    assert_type(ada, AsyncFireObject[UserProfile])


def subcollection_binding(user: FireObject[UserProfile]) -> None:
    """Subcollections accept schema annotations at creation time."""
    orders = user.collection("orders", Order)
    assert_type(orders, FireCollection[Order])
