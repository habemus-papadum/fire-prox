"""Static typing fixture for post-hoc schema binding (positive case)."""

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


def expects_user(user: TypedFireObject[UserProfile]) -> str:
    """Return the display name to ensure attribute typing works."""

    return user.display_name


# Pretend we received fully-initialized collections from FireProx.
users = cast(FireCollection[UserProfile], None)
orders = cast(FireCollection[Order], None)

user_doc = users.new()
user_view = user_doc.schema_view()
user_view.display_name = "Ada"
user_view.age = 36

order_doc = orders.new()
order_view = order_doc.schema_view()
# Document reference assignment coming from another collection.
user_ref = cast(DocRef[UserProfile], None)
order_view.purchaser = user_ref
order_view.total = 199.0

# Method chaining remains available on the FireObject wrapper.
order_doc.save().delete()

# Functions consuming typed objects see the dataclass fields.
expects_user(user_view)
