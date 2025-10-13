"""Static typing fixture that should trigger Pyright errors."""

# pyright: strict

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from fire_prox import DocRef, FireCollection, TypedFireObject


@dataclass
class UserProfile:
    display_name: str
    age: int


@dataclass
class Order:
    purchaser: DocRef[UserProfile]
    total: float


users = cast(FireCollection[UserProfile], None)
orders = cast(FireCollection[Order], None)

bad_user: TypedFireObject[UserProfile] = users.new()
bad_user_view = bad_user.schema_view()
bad_user_view.age = "invalid"

bad_order = orders.new()
bad_order_view = bad_order.schema_view()
bad_order_view.total = "not-a-number"
