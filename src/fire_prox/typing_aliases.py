"""Type aliases that improve static typing for Fire-Prox objects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - type-checker only utilities
    from typing import TypeVar

    from typing_extensions import TypeAliasType

    from .async_fire_object import AsyncFireObject
    from .fire_object import FireObject

    SchemaT = TypeVar("SchemaT")

    TypedFireObject = TypeAliasType(
        "TypedFireObject",
        FireObject[SchemaT] & SchemaT,
        type_params=(SchemaT,),
    )

    TypedAsyncFireObject = TypeAliasType(
        "TypedAsyncFireObject",
        AsyncFireObject[SchemaT] & SchemaT,
        type_params=(SchemaT,),
    )
else:  # pragma: no cover - runtime fallback
    TypedFireObject = Any
    TypedAsyncFireObject = Any

__all__ = ["TypedFireObject", "TypedAsyncFireObject"]

