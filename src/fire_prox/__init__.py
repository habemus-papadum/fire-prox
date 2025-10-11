"""Core Fire-Prox primitives.

The project currently focuses on implementing the foundational behaviours described in
``Architectural_Blueprint.md``.  This module therefore provides a functional
implementation for the Phase 1 roadmap (the ``FireObject`` proxy and its state
machine) while defining typed stubs for the later phases.  The stubs expose the
intended public API surface so that downstream code – and future contributors –
can reason about integration points today without committing to a concrete
implementation prematurely.

Future phases will flesh out the stubbed classes/methods with the behaviour
outlined in the blueprint (dirty field tracking, subcollections, advanced query
builder, mutation-tracking containers, etc.).  Each stub documents the expected
responsibilities to make subsequent iterations straightforward.
"""

from __future__ import annotations

import asyncio
from enum import Enum, auto
from typing import Any, AsyncIterator, Dict, Iterable, Iterator, MutableMapping, MutableSequence, Optional, Self

__all__ = ["FireObjectState", "FireObject", "FireCollection", "FireProx", "FireQuery", "ProxiedMap", "ProxiedList"]


from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from google.cloud.firestore_v1 import Client
    from google.cloud.firestore_v1 import CollectionReference, DocumentReference
    from google.cloud.firestore_v1 import DocumentSnapshot
else:  # pragma: no cover - runtime fallback types to keep annotations useful
    Client = Any  # type: ignore[misc,assignment]
    CollectionReference = Any  # type: ignore[misc,assignment]
    DocumentReference = Any  # type: ignore[misc,assignment]
    DocumentSnapshot = Any  # type: ignore[misc,assignment]


class FireObjectState(Enum):
    """Lifecycle states for :class:`FireObject` instances."""

    DETACHED = auto()
    ATTACHED = auto()
    LOADED = auto()
    DELETED = auto()


_INTERNAL_ATTRS = {
    "_data",
    "_state",
    "_reference",
    "_collection_ref",
    "_dirty",
}

class FireObject:
    """State-aware proxy that represents a Firestore document.

    Parameters
    ----------
    reference:
        A Firestore ``DocumentReference`` that the object should attach to.  If
        ``None`` is provided the object starts in the ``DETACHED`` state and
        relies on an associated :class:`FireCollection` to create a new document
        when :meth:`save` is invoked.
    state:
        Optional explicit state value.  When omitted the constructor infers the
        state from the presence of ``reference``.
    data:
        Initial field values for the proxy.
    collection_ref:
        Optional ``CollectionReference`` to use when a detached object is
        first saved.

    Notes
    -----
    The class implements all behaviours promised for Phase 1 of the roadmap:

    * state machine transitions (``DETACHED`` → ``ATTACHED`` → ``LOADED`` → ``DELETED``)
    * lazy fetching on attribute access
    * simple, full-document ``save`` and ``delete`` operations
    * basic dirty flag tracking

    All mutation-oriented magic methods delegate to the internal ``_data``
    dictionary which keeps the proxy schemaless and dynamic.
    """

    def __init__(
        self,
        reference: Optional[DocumentReference] = None,
        *,
        state: Optional[FireObjectState] = None,
        data: Optional[Dict[str, Any]] = None,
        collection_ref: Optional[CollectionReference] = None,
    ) -> None:
        object.__setattr__(self, "_reference", reference)
        object.__setattr__(self, "_collection_ref", collection_ref)
        object.__setattr__(self, "_data", dict(data or {}))
        initial_state = state or (FireObjectState.ATTACHED if reference is not None else FireObjectState.DETACHED)
        object.__setattr__(self, "_state", initial_state)
        object.__setattr__(self, "_dirty", bool(data))

    # ------------------------------------------------------------------
    # Phase 1 implementation
    # ------------------------------------------------------------------
    @property
    def reference(self) -> Optional[DocumentReference]:
        """Return the underlying ``DocumentReference`` if attached."""

        return self._reference

    @property
    def state(self) -> FireObjectState:
        """Current :class:`FireObjectState` of the proxy."""

        return self._state

    def is_attached(self) -> bool:
        """Return ``True`` when the object is bound to a document reference."""

        return self._state in {FireObjectState.ATTACHED, FireObjectState.LOADED}

    def is_loaded(self) -> bool:
        """Return ``True`` when the object's data has been fetched from Firestore."""

        return self._state is FireObjectState.LOADED

    def is_dirty(self) -> bool:
        """Return ``True`` if data has been modified since the last fetch/save."""

        return self._dirty

    def is_deleted(self) -> bool:
        """Return ``True`` if the object represents a deleted document."""

        return self._state is FireObjectState.DELETED

    def to_dict(self) -> Dict[str, Any]:
        """Return a shallow copy of the cached document data."""

        return dict(self._data)

    def fetch(self) -> None:
        """Synchronously fetch the remote document data into the proxy cache."""

        if self._state is FireObjectState.DELETED:
            raise RuntimeError("Cannot fetch a deleted FireObject.")
        if self._reference is None:
            raise RuntimeError("Cannot fetch data for a detached FireObject without a document reference.")

        snapshot: DocumentSnapshot = self._reference.get()
        if getattr(snapshot, "exists", False):
            data = snapshot.to_dict() or {}
            object.__setattr__(self, "_data", dict(data))
            object.__setattr__(self, "_dirty", False)
            object.__setattr__(self, "_state", FireObjectState.LOADED)
        else:
            object.__setattr__(self, "_data", {})
            object.__setattr__(self, "_dirty", False)
            object.__setattr__(self, "_state", FireObjectState.ATTACHED)

    async def fetch_async(self) -> None:
        """Asynchronous wrapper around :meth:`fetch`."""

        await asyncio.to_thread(self.fetch)

    def save(self, *, doc_id: Optional[str] = None) -> None:
        """Synchronously persist the proxy's current state to Firestore.

        Parameters
        ----------
        doc_id:
            Optional explicit document ID to use when the object is in the
            ``DETACHED`` state.  When omitted Firestore's auto-ID mechanism is
            used via :meth:`CollectionReference.document`.
        """

        if self._state is FireObjectState.DELETED:
            raise RuntimeError("Cannot save a deleted FireObject.")

        reference = self._reference
        if reference is None:
            if self._collection_ref is None:
                raise RuntimeError("Detached FireObject cannot be saved without an associated collection reference.")
            if doc_id is not None:
                reference = self._collection_ref.document(doc_id)
            else:
                reference = self._collection_ref.document()
            object.__setattr__(self, "_reference", reference)

        reference.set(self._data)
        object.__setattr__(self, "_dirty", False)
        object.__setattr__(self, "_state", FireObjectState.LOADED)

    async def save_async(self, *, doc_id: Optional[str] = None) -> None:
        """Asynchronous wrapper around :meth:`save`."""

        await asyncio.to_thread(self.save, doc_id=doc_id)

    def delete(self) -> None:
        """Synchronously delete the remote document represented by the proxy."""

        if self._state is FireObjectState.DELETED:
            return

        if self._reference is None:
            # Nothing exists remotely; treat as a logical delete.
            object.__setattr__(self, "_state", FireObjectState.DELETED)
            object.__setattr__(self, "_data", {})
            object.__setattr__(self, "_dirty", False)
            return

        self._reference.delete()
        object.__setattr__(self, "_state", FireObjectState.DELETED)
        object.__setattr__(self, "_data", {})
        object.__setattr__(self, "_dirty", False)

    async def delete_async(self) -> None:
        """Asynchronous wrapper around :meth:`delete`."""

        await asyncio.to_thread(self.delete)

    # ------------------------------------------------------------------
    # Python data model overrides for schemaless attribute handling
    # ------------------------------------------------------------------
    def __getattr__(self, name: str) -> Any:
        if name in _INTERNAL_ATTRS:
            return object.__getattribute__(self, name)

        if name in self._data:
            return self._data[name]

        if self._state is FireObjectState.ATTACHED:
            self.fetch()
            if name in self._data:
                return self._data[name]

        raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in _INTERNAL_ATTRS or name.startswith("_"):
            object.__setattr__(self, name, value)
            return

        self._data[name] = value
        object.__setattr__(self, "_dirty", True)

    def __delattr__(self, name: str) -> None:
        if name in _INTERNAL_ATTRS or name.startswith("_"):
            raise AttributeError(f"Cannot delete internal attribute '{name}'.")

        if name not in self._data:
            raise AttributeError(name)

        del self._data[name]
        object.__setattr__(self, "_dirty", True)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<FireObject state={self._state!r} data={self._data!r}>"

    # ------------------------------------------------------------------
    # Phase 2+ stubs
    # ------------------------------------------------------------------
    @classmethod
    def from_snapshot(cls, snapshot: DocumentSnapshot, *, attach_lazy: bool = True) -> FireObject:
        """Create a proxy from a Firestore ``DocumentSnapshot``.

        Parameters
        ----------
        snapshot:
            The Firestore snapshot to hydrate.
        attach_lazy:
            When ``True`` the resulting object should treat nested references as
            lazily loaded proxies instead of immediately fetching their data.

        Notes
        -----
        This method is part of the Phase 2 roadmap.  The stub exists so that
        callers can type-check against the eventual API.  It currently raises
        ``NotImplementedError`` to signal that the behaviour is forthcoming.
        """

        raise NotImplementedError

    def collection(self, name: str) -> "FireCollection":
        """Return a subcollection accessor for this document (Phase 2 feature)."""

        raise NotImplementedError

    def partial_update(self) -> None:
        """Perform an efficient partial update (Phase 2 feature stub)."""

        raise NotImplementedError


class FireCollection:
    """Represents a Firestore collection within the Fire-Prox API surface."""

    def __init__(self, reference: CollectionReference):
        self._reference = reference

    @property
    def reference(self) -> CollectionReference:
        """Return the underlying ``CollectionReference``."""

        return self._reference

    def new(self) -> FireObject:
        """Return a detached :class:`FireObject` ready to be populated and saved."""

        return FireObject(collection_ref=self._reference)

    def doc(self, doc_id: str) -> FireObject:
        """Return an attached :class:`FireObject` for the given document ID."""

        reference = self._reference.document(doc_id)
        return FireObject(reference=reference, state=FireObjectState.ATTACHED)

    # ------------------------------------------------------------------
    # Phase 2+ stubs
    # ------------------------------------------------------------------
    def where(self, field: str, op: str, value: Any) -> "FireQuery":
        """Return a query constrained by the provided filter (stub)."""

        raise NotImplementedError

    def order_by(self, field: str, *, direction: str = "asc") -> "FireQuery":
        """Return a query with ordering applied (stub)."""

        raise NotImplementedError

    def limit(self, count: int) -> "FireQuery":
        """Return a query limited to ``count`` results (stub)."""

        raise NotImplementedError


class FireProx:
    """Convenience facade wrapping a native Firestore ``Client`` instance."""

    def __init__(self, client: Client):
        self._client = client

    @property
    def client(self) -> Client:
        """Return the underlying Firestore client."""

        return self._client

    def doc(self, path: str) -> FireObject:
        """Return an attached :class:`FireObject` for ``path``."""

        if not path:
            raise ValueError("Document path must be a non-empty string.")
        reference = self._client.document(path)
        return FireObject(reference=reference, state=FireObjectState.ATTACHED)

    def collection(self, path: str) -> FireCollection:
        """Return a :class:`FireCollection` wrapper for ``path``."""

        if not path:
            raise ValueError("Collection path must be a non-empty string.")
        reference = self._client.collection(path)
        return FireCollection(reference)


class FireQuery:
    """Stub for the Phase 2 query builder abstraction."""

    def __init__(self, collection: FireCollection):
        self._collection = collection

    def where(self, field: str, op: str, value: Any) -> Self:
        """Add a filter clause to the query (stub)."""

        raise NotImplementedError

    def order_by(self, field: str, *, direction: str = "asc") -> Self:
        """Add an ordering clause to the query (stub)."""

        raise NotImplementedError

    def limit(self, count: int) -> Self:
        """Limit the number of results returned (stub)."""

        raise NotImplementedError

    def stream(self) -> Iterator[FireObject]:
        """Stream query results as :class:`FireObject` instances (stub)."""

        raise NotImplementedError

    async def stream_async(self) -> AsyncIterator[FireObject]:
        """Asynchronous result stream (stub)."""

        raise NotImplementedError

    def get(self) -> Iterable[FireObject]:
        """Materialise all query results (stub)."""

        raise NotImplementedError

    async def get_async(self) -> Iterable[FireObject]:
        """Asynchronous query execution returning hydrated objects (stub)."""

        raise NotImplementedError


class ProxiedMap(MutableMapping[str, Any]):
    """Mutation-tracking dictionary wrapper planned for Phase 3."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError

    def __getitem__(self, key: str) -> Any:
        raise NotImplementedError

    def __setitem__(self, key: str, value: Any) -> None:
        raise NotImplementedError

    def __delitem__(self, key: str) -> None:
        raise NotImplementedError

    def __iter__(self) -> Iterator[str]:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError


class ProxiedList(MutableSequence[Any]):
    """Mutation-tracking list wrapper planned for Phase 3."""

    def __init__(self, iterable: Optional[Iterable[Any]] = None) -> None:
        raise NotImplementedError

    def __getitem__(self, index: int) -> Any:
        raise NotImplementedError

    def __setitem__(self, index: int, value: Any) -> None:
        raise NotImplementedError

    def __delitem__(self, index: int) -> None:
        raise NotImplementedError

    def insert(self, index: int, value: Any) -> None:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError

