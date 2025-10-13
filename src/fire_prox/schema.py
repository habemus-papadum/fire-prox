"""Utilities for post-hoc schema typing metadata and helpers."""

from __future__ import annotations

from dataclasses import dataclass, is_dataclass
from typing import Any, Optional, TypeVar, get_args, get_origin, get_type_hints

from google.cloud.firestore_v1.async_document import AsyncDocumentReference
from google.cloud.firestore_v1.document import DocumentReference
from typing_extensions import TypeAliasType

try:  # Python 3.12+: Annotated available from typing
    from typing import Annotated
except ImportError:  # pragma: no cover - safety for older Python
    from typing_extensions import Annotated

DOC_REF_MARKER = "fire_prox.DocumentReference"

SchemaT = TypeVar("SchemaT")

DocRef = TypeAliasType(
    "DocRef",
    Annotated[DocumentReference, (DOC_REF_MARKER, SchemaT)],
    type_params=(SchemaT,),
)

AsyncDocRef = TypeAliasType(
    "AsyncDocRef",
    Annotated[AsyncDocumentReference, (DOC_REF_MARKER, SchemaT)],
    type_params=(SchemaT,),
)


@dataclass(frozen=True)
class SchemaField:
    """Metadata captured for a dataclass field."""

    name: str
    annotation: Any
    is_document_reference: bool
    reference_target: Optional[Any]


@dataclass(frozen=True)
class SchemaMetadata:
    """Metadata describing an attached dataclass schema."""

    schema_type: type[Any]
    fields: tuple[SchemaField, ...]


def analyze_dataclass_schema(schema: type[Any]) -> SchemaMetadata:
    """Return lightweight metadata for a dataclass schema."""

    if not is_dataclass(schema):
        raise TypeError("Schema binding requires a dataclass type")

    hints = get_type_hints(schema, include_extras=True)
    field_metadata: list[SchemaField] = []

    for name, annotation in hints.items():
        is_doc_ref, target = _extract_doc_ref(annotation)
        field_metadata.append(
            SchemaField(
                name=name,
                annotation=annotation,
                is_document_reference=is_doc_ref,
                reference_target=target,
            )
        )

    return SchemaMetadata(schema_type=schema, fields=tuple(field_metadata))


def _extract_doc_ref(annotation: Any) -> tuple[bool, Optional[Any]]:
    """Detect whether an annotation represents a document reference."""

    origin = get_origin(annotation)
    if origin is Annotated:
        args = get_args(annotation)
        base = args[0]
        metadata = args[1:]
        for meta in metadata:
            marker, target = _normalize_metadata(meta)
            if marker == DOC_REF_MARKER:
                return True, target
        # Fallback to the underlying annotation when marker missing.
        return _extract_doc_ref(base)

    return False, None


def _normalize_metadata(metadata: Any) -> tuple[Any, Optional[Any]]:
    """Normalize Annotated metadata tuples for easier inspection."""

    if isinstance(metadata, tuple):
        if not metadata:
            return metadata, None
        marker = metadata[0]
        target = metadata[1] if len(metadata) > 1 else None
        return marker, target
    return metadata, None


__all__ = [
    "DOC_REF_MARKER",
    "DocRef",
    "AsyncDocRef",
    "SchemaField",
    "SchemaMetadata",
    "analyze_dataclass_schema",
]

