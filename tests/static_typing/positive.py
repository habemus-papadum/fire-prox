"""Static typing fixtures that should pass without errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from typing_extensions import assert_type

from fire_prox import FireCollection, FireObject, FireProx


@dataclass
class UserProfile:
    display_name: str
    age: int


@dataclass
class Order:
    total_cents: int
    status: str


def direct_binding(db: FireProx) -> None:
    """Passing a schema to collection() returns a typed collection."""
    users = db.collection("users", UserProfile)
    assert_type(users, FireCollection[UserProfile])
    doc = users.doc("ada")
    assert_type(doc, FireObject[UserProfile])


def default_collection(db: FireProx) -> None:
    """Omitting schema preserves the legacy dynamic typing."""
    users = db.collection("users")
    assert_type(users, FireCollection[object])


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


def subcollection_binding(user: FireObject[object]) -> None:
    """Subcollections accept schemas directly."""
    orders = user.collection("orders", Order)
    assert_type(orders, FireCollection[Order])
    order = orders.doc("order-1")
    assert_type(order, FireObject[Order])
