from typing import Any, Generic, TypeVar, overload

from google.cloud.firestore_v1.document import DocumentSnapshot

SchemaT_co = TypeVar("SchemaT_co", covariant=True, bound=object)
SchemaT = TypeVar("SchemaT", bound=object)

from .base_fire_object import BaseFireObject
from .fire_collection import FireCollection


class FireObject(BaseFireObject[SchemaT_co], SchemaT_co, Generic[SchemaT_co]):
    schema_type: type[SchemaT_co] | None

    def fetch(self, force: bool = False, transaction: Any | None = None) -> FireObject[SchemaT_co]: ...

    def save(
        self,
        doc_id: str | None = None,
        transaction: Any | None = None,
        batch: Any | None = None,
    ) -> FireObject[SchemaT_co]: ...

    def delete(self, batch: Any | None = None) -> None: ...

    @overload
    def collection(self, name: str) -> FireCollection[object]: ...

    @overload
    def collection(self, name: str, schema: type[SchemaT]) -> FireCollection[SchemaT]: ...

    @classmethod
    def from_snapshot(
        cls,
        snapshot: DocumentSnapshot,
        parent_collection: Any | None = None,
        sync_client: Any | None = None,
    ) -> FireObject[SchemaT_co]: ...
