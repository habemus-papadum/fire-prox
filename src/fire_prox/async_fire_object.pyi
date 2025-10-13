from typing import Any, Generic, TypeVar

from typing import Any, Generic, TypeVar, overload

from google.cloud.firestore_v1.document import DocumentSnapshot

SchemaT_co = TypeVar("SchemaT_co", covariant=True, bound=object)
SchemaT = TypeVar("SchemaT", bound=object)
SchemaType = type[SchemaT_co]

from .base_fire_object import BaseFireObject
from .async_fire_collection import AsyncFireCollection


class AsyncFireObject(BaseFireObject[SchemaT_co], SchemaT_co, Generic[SchemaT_co]):
    schema_type: SchemaType | None

    async def fetch(
        self,
        force: bool = False,
        transaction: Any | None = None,
    ) -> AsyncFireObject[SchemaT_co]: ...

    async def save(
        self,
        doc_id: str | None = None,
        transaction: Any | None = None,
        batch: Any | None = None,
    ) -> AsyncFireObject[SchemaT_co]: ...

    async def delete(self, batch: Any | None = None) -> None: ...

    @classmethod
    def from_snapshot(
        cls,
        snapshot: DocumentSnapshot,
        parent_collection: Any | None = None,
        sync_client: Any | None = None,
    ) -> AsyncFireObject[SchemaT_co]: ...

    @overload
    def collection(self, name: str) -> AsyncFireCollection[object]: ...

    @overload
    def collection(
        self,
        name: str,
        schema: type[SchemaT],
    ) -> AsyncFireCollection[SchemaT]: ...

    def collection(
        self,
        name: str,
        schema: type[SchemaT] | None = ...,
    ) -> AsyncFireCollection[SchemaT]: ...
