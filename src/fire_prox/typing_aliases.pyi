from typing import TypeVar

from .async_fire_object import AsyncFireObject
from .fire_object import FireObject

SchemaT = TypeVar("SchemaT", covariant=True)

type TypedFireObject[SchemaT] = FireObject[SchemaT] & SchemaT
type TypedAsyncFireObject[SchemaT] = AsyncFireObject[SchemaT] & SchemaT
