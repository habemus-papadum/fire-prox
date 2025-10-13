"""
BaseFireObject: Shared logic for sync and async FireObject implementations.

This module contains the base class that implements all logic that is
identical between synchronous and asynchronous FireObject implementations.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Optional, Set

from google.cloud import firestore
from google.cloud.exceptions import NotFound
from google.cloud.firestore_v1.async_document import AsyncDocumentReference
from google.cloud.firestore_v1.document import DocumentReference, DocumentSnapshot
from google.cloud.firestore_v1.vector import Vector

from .state import State


class _SaveAction(Enum):
    """Internal enum describing the type of write to perform."""

    NOOP = auto()
    CREATE = auto()
    SET = auto()
    UPDATE = auto()


@dataclass
class _SavePlan:
    """Structured description of the work required for ``save``."""

    action: _SaveAction
    doc_ref: Optional[Any] = None
    payload: Optional[Dict[str, Any]] = None


class BaseFireObject:
    """
    Base class for FireObject implementations (sync and async).

    Contains all shared logic:
    - State management
    - State inspection methods
    - Dirty tracking
    - Data dictionary management
    - Property accessors
    - String representations

    Subclasses must implement:
    - fetch() - with appropriate sync/async signature
    - save() - with appropriate sync/async signature
    - delete() - with appropriate sync/async signature
    - __getattr__() - may need async support for lazy loading
    """

    # Class-level constants for internal attribute names
    _INTERNAL_ATTRS = {
        '_doc_ref', '_sync_doc_ref', '_sync_client', '_data', '_state', '_dirty_fields',
        '_deleted_fields', '_atomic_ops', '_parent_collection', '_client', '_id', '_path'
    }

    def __init__(
        self,
        doc_ref: Optional[DocumentReference] = None,
        initial_state: Optional[State] = None,
        parent_collection: Optional[Any] = None,
        sync_doc_ref: Optional[DocumentReference] = None,
        sync_client: Optional[Any] = None
    ):
        """
        Initialize a FireObject.

        Args:
            doc_ref: Optional DocumentReference from native client.
            initial_state: Initial state (defaults to DETACHED if no doc_ref,
                          ATTACHED if doc_ref provided).
            parent_collection: Optional reference to parent FireCollection
                             (needed for save() on DETACHED objects).
            sync_doc_ref: Optional sync DocumentReference (for async lazy loading).
            sync_client: Optional sync Firestore Client (for async subcollections).
        """
        # Set internal attributes directly to avoid __setattr__ logic
        object.__setattr__(self, '_doc_ref', doc_ref)
        object.__setattr__(self, '_sync_doc_ref', sync_doc_ref)
        object.__setattr__(self, '_sync_client', sync_client)
        object.__setattr__(self, '_data', {})
        object.__setattr__(self, '_parent_collection', parent_collection)

        # Determine initial state
        if initial_state is not None:
            object.__setattr__(self, '_state', initial_state)
        elif doc_ref is None:
            object.__setattr__(self, '_state', State.DETACHED)
        else:
            object.__setattr__(self, '_state', State.ATTACHED)

        # Field-level dirty tracking (Phase 2)
        # Track which fields have been modified or deleted since last save/fetch
        object.__setattr__(self, '_dirty_fields', set())
        object.__setattr__(self, '_deleted_fields', set())

        # Atomic operations tracking (Phase 2)
        # Store atomic operations (ArrayUnion, ArrayRemove, Increment) to apply on save
        object.__setattr__(self, '_atomic_ops', {})

    # =========================================================================
    # State Inspection (SHARED)
    # =========================================================================

    @property
    def state(self) -> State:
        """Get current state of the object."""
        return self._state

    def is_detached(self) -> bool:
        """Check if object is in DETACHED state."""
        return self._state == State.DETACHED

    def is_attached(self) -> bool:
        """Check if object has a DocumentReference (ATTACHED or LOADED)."""
        return self._state in (State.ATTACHED, State.LOADED)

    def is_loaded(self) -> bool:
        """Check if object is in LOADED state."""
        return self._state == State.LOADED

    def is_deleted(self) -> bool:
        """Check if object is in DELETED state."""
        return self._state == State.DELETED

    def is_dirty(self) -> bool:
        """Check if object has unsaved changes."""
        if self._state == State.DETACHED:
            return True  # DETACHED is always dirty
        return (len(self._dirty_fields) > 0 or
                len(self._deleted_fields) > 0 or
                len(self._atomic_ops) > 0)

    @property
    def dirty_fields(self) -> Set[str]:
        """Get the set of modified field names (Phase 2)."""
        return self._dirty_fields.copy()

    @property
    def deleted_fields(self) -> Set[str]:
        """Get the set of deleted field names (Phase 2)."""
        return self._deleted_fields.copy()

    # =========================================================================
    # Document Identity (SHARED)
    # =========================================================================

    @property
    def id(self) -> Optional[str]:
        """Get document ID, or None if DETACHED."""
        return self._doc_ref.id if self._doc_ref else None

    @property
    def path(self) -> Optional[str]:
        """Get full document path, or None if DETACHED."""
        return self._doc_ref.path if self._doc_ref else None

    # =========================================================================
    # Transaction Support (Phase 2)
    # =========================================================================

    def transaction(self) -> Any:
        """
        Create a transaction for atomic read-modify-write operations.

        Convenience method for creating transactions directly from a document
        reference, eliminating the need to access the root FireProx client.

        Returns:
            A native google.cloud.firestore.Transaction or
            google.cloud.firestore.AsyncTransaction instance.

        Raises:
            ValueError: If called on a DETACHED object (no document path yet).

        Example:
            user = db.doc('users/alice')
            transaction = user.transaction()

            @firestore.transactional
            def update_credits(transaction):
                user.fetch(transaction=transaction)
                user.credits += 10
                user.save(transaction=transaction)

            update_credits(transaction)
        """
        self._validate_not_detached("transaction()")

        # Get the client from the document reference
        return self._doc_ref._client.transaction()

    def batch(self) -> Any:
        """
        Create a batch for accumulating multiple write operations.

        Convenience method for creating batches directly from a document
        reference, eliminating the need to access the root FireProx client.

        Returns:
            A native google.cloud.firestore.WriteBatch or
            google.cloud.firestore.AsyncWriteBatch instance.

        Raises:
            ValueError: If called on a DETACHED object (no document path yet).

        Example:
            user = db.doc('users/alice')
            batch = user.batch()

            # Use the batch for multiple operations
            user.credits = 100
            user.save(batch=batch)

            other_user = db.doc('users/bob')
            other_user.delete(batch=batch)

            # Commit all operations atomically
            batch.commit()

        Note:
            See BaseFireProx.batch() for detailed documentation on batch operations.
        """
        self._validate_not_detached("batch()")

        # Get the client from the document reference
        return self._doc_ref._client.batch()

    # =========================================================================
    # Subcollections (Phase 2)
    # =========================================================================

    def collection(self, name: str) -> Any:
        """
        Get a subcollection reference for this document.

        Phase 2 feature. Returns a collection reference for a subcollection
        under this document, enabling hierarchical data structures.

        Args:
            name: Name of the subcollection.

        Returns:
            FireCollection or AsyncFireCollection instance for the subcollection.

        Raises:
            ValueError: If called on a DETACHED object (no document path yet).
            RuntimeError: If called on a DELETED object.

        Example:
            user = db.doc('users/alovelace')
            posts = user.collection('posts')  # Gets 'users/alovelace/posts'
            new_post = posts.new()
            new_post.title = "On Analytical Engines"
            new_post.save()
        """
        self._validate_not_detached("collection()")
        self._validate_not_deleted("collection()")

        # Get subcollection reference from document reference
        subcollection_ref = self._doc_ref.collection(name)

        # Import here to avoid circular dependency
        from .async_fire_collection import AsyncFireCollection
        from .fire_collection import FireCollection

        # Return appropriate collection type based on client type
        # The concrete class will override this if needed
        if hasattr(self._doc_ref, '__class__') and 'Async' in self._doc_ref.__class__.__name__:
            return AsyncFireCollection(
                subcollection_ref,
                client=None,  # Will be inferred from ref
                sync_client=self._sync_client if hasattr(self, '_sync_client') else None
            )
        else:
            return FireCollection(subcollection_ref, client=None)

    # =========================================================================
    # Atomic Operations (Phase 2)
    # =========================================================================

    def array_union(self, field: str, values: list) -> None:
        """
        Mark field for ArrayUnion operation and simulate locally.

        Phase 2 feature. ArrayUnion adds elements to an array field without
        reading the document first. If the array doesn't exist, it creates it.
        Duplicate values are automatically deduplicated.

        The operation is simulated locally, so the array is immediately
        updated in memory. This eliminates the need to call fetch() after save().

        Mutual Exclusivity: A field can be either modified directly (vanilla) OR
        via atomic operations, but not both. Once array_union() is called on a field,
        you cannot modify that field directly until after save().

        Args:
            field: The field name to apply ArrayUnion to.
            values: List of values to add to the array.

        Raises:
            RuntimeError: If called on a DELETED object.
            ValueError: If the field has been modified directly (is dirty).

        Example:
            user = db.doc('users/ada')
            user.array_union('tags', ['python', 'firestore'])
            user.save()  # No fetch() needed - local state is already updated!
        """
        self._validate_not_deleted("array_union()")

        # Validate field is not dirty (mutual exclusivity)
        if field in self._dirty_fields:
            raise ValueError(
                f"Cannot perform atomic array_union on field '{field}' - "
                f"field has been modified directly. Save changes first or use atomic operations exclusively."
            )

        # Simulate locally: get current array (default to []) and add unique values
        current_array = self._data.get(field, [])
        # Add only values that aren't already in the array (deduplication)
        updated_array = current_array + [v for v in values if v not in current_array]
        self._data[field] = updated_array

        # Store the operation for server-side execution
        from google.cloud import firestore
        self._atomic_ops[field] = firestore.ArrayUnion(values)

    def array_remove(self, field: str, values: list) -> None:
        """
        Mark field for ArrayRemove operation and simulate locally.

        Phase 2 feature. ArrayRemove removes specified elements from an array
        field without reading the document first.

        The operation is simulated locally, so the array is immediately
        updated in memory. This eliminates the need to call fetch() after save().

        Mutual Exclusivity: A field can be either modified directly (vanilla) OR
        via atomic operations, but not both. Once array_remove() is called on a field,
        you cannot modify that field directly until after save().

        Args:
            field: The field name to apply ArrayRemove to.
            values: List of values to remove from the array.

        Raises:
            RuntimeError: If called on a DELETED object.
            ValueError: If the field has been modified directly (is dirty).

        Example:
            user = db.doc('users/ada')
            user.array_remove('tags', ['deprecated'])
            user.save()  # No fetch() needed - local state is already updated!
        """
        self._validate_not_deleted("array_remove()")

        # Validate field is not dirty (mutual exclusivity)
        if field in self._dirty_fields:
            raise ValueError(
                f"Cannot perform atomic array_remove on field '{field}' - "
                f"field has been modified directly. Save changes first or use atomic operations exclusively."
            )

        # Simulate locally: filter out values to remove
        current_array = self._data.get(field, [])
        updated_array = [item for item in current_array if item not in values]
        self._data[field] = updated_array

        # Store the operation for server-side execution
        from google.cloud import firestore
        self._atomic_ops[field] = firestore.ArrayRemove(values)

    def increment(self, field: str, value: float) -> None:
        """
        Mark field for Increment operation and simulate locally.

        Phase 2 feature. Increment atomically increments a numeric field by the
        given value without reading the document first. If the field doesn't
        exist, it treats it as 0.

        The operation is simulated locally, so the field value is immediately
        updated in memory. This eliminates the need to call fetch() after save().

        Mutual Exclusivity: A field can be either modified directly (vanilla) OR
        via atomic operations, but not both. Once increment() is called on a field,
        you cannot modify that field directly until after save().

        Args:
            field: The field name to increment.
            value: The amount to increment by (can be negative to decrement).

        Raises:
            RuntimeError: If called on a DELETED object.
            ValueError: If the field has been modified directly (is dirty).

        Example:
            user = db.doc('users/ada')
            user.increment('view_count', 1)
            user.increment('score', -5)  # Decrement by 5
            user.save()  # No fetch() needed - local state is already updated!
        """
        self._validate_not_deleted("increment()")

        # Validate field is not dirty (mutual exclusivity)
        if field in self._dirty_fields:
            raise ValueError(
                f"Cannot perform atomic increment on field '{field}' - "
                f"field has been modified directly. Save changes first or use atomic operations exclusively."
            )

        # Simulate locally: get current value (default to 0) and add increment
        current_value = self._data.get(field, 0)
        self._data[field] = current_value + value

        # Store the operation for server-side execution
        from google.cloud import firestore
        self._atomic_ops[field] = firestore.Increment(value)

    # =========================================================================
    # Attribute Handling (SHARED - but __getattr__ may need override)
    # =========================================================================

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Store attribute in _data dictionary and track in dirty fields.

        Internal attributes (starting with _) are stored directly on object.

        Phase 2: Track field-level changes for efficient partial updates.
        Enforces mutual exclusivity between vanilla and atomic operations.
        """
        # Internal attributes bypass _data storage
        if name in self._INTERNAL_ATTRS:
            object.__setattr__(self, name, value)
            return

        # Cannot modify DELETED objects
        if hasattr(self, '_state') and self._state == State.DELETED:
            raise AttributeError("Cannot modify a DELETED FireObject")

        # Initialize phase - before _data exists
        if not hasattr(self, '_data'):
            object.__setattr__(self, name, value)
        else:
            # Enforce mutual exclusivity: cannot modify field with pending atomic operation
            if hasattr(self, '_atomic_ops') and name in self._atomic_ops:
                raise ValueError(
                    "Cannot modify field "
                    f"'{name}' directly - field has a pending atomic operation. "
                    "Save changes first or use vanilla modifications exclusively."
                )

            # Convert special types for storage (FireObject → DocumentReference, FireVector → Vector, etc.)
            value = self._convert_value_for_storage(value)

            # Store in _data and track in dirty fields
            self._data[name] = value
            self._dirty_fields.add(name)
            # If this field was marked for deletion, remove it from deleted set
            self._deleted_fields.discard(name)

    def __delattr__(self, name: str) -> None:
        """
        Remove field from _data and track in deleted fields.

        Phase 2: Track deletions for efficient partial updates with DELETE_FIELD.
        """
        if self._state == State.DELETED:
            raise AttributeError("Cannot delete attributes from a DELETED FireObject")

        if name not in self._data:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        del self._data[name]
        # Track deletion for partial update
        self._deleted_fields.add(name)
        # Remove from dirty fields if it was there
        self._dirty_fields.discard(name)

    # =========================================================================
    # Utility Methods (SHARED)
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """
        Return shallow copy of internal data.

        Returns:
            Dictionary containing all document fields.

        Raises:
            RuntimeError: If object is in ATTACHED state (data not loaded).
        """
        if self._state == State.ATTACHED:
            raise RuntimeError("Cannot call to_dict() on ATTACHED FireObject. Call fetch() first.")

        return dict(self._data)

    def __repr__(self) -> str:
        """Return detailed string representation."""
        if self._state == State.DETACHED:
            return f"<{type(self).__name__} DETACHED dirty_fields={len(self._dirty_fields)}>"
        dirty_count = len(self._dirty_fields) + len(self._deleted_fields)
        return f"<{type(self).__name__} {self._state.name} path='{self.path}' dirty_fields={dirty_count}>"

    def __str__(self) -> str:
        """Return human-readable string representation."""
        if self._state == State.DETACHED:
            return f"{type(self).__name__}(detached)"
        return f"{type(self).__name__}({self.path})"

    # =========================================================================
    # Protected Helper Methods (SHARED)
    # =========================================================================

    def _validate_not_deleted(self, operation: str) -> None:
        """
        Validate that object is not in DELETED state.

        Args:
            operation: Name of operation being attempted.

        Raises:
            RuntimeError: If object is DELETED.
        """
        if self._state == State.DELETED:
            raise RuntimeError(f"Cannot {operation} on a DELETED FireObject")

    def _validate_not_detached(self, operation: str) -> None:
        """
        Validate that object is not in DETACHED state.

        Args:
            operation: Name of operation being attempted.

        Raises:
            ValueError: If object is DETACHED.
        """
        if self._state == State.DETACHED:
            raise ValueError(f"Cannot {operation} on a DETACHED FireObject (no DocumentReference)")

    def _mark_clean(self) -> None:
        """Mark object as clean (no unsaved changes)."""
        self._dirty_fields.clear()
        self._deleted_fields.clear()
        self._atomic_ops.clear()

    def _prepare_data_for_storage(self) -> Dict[str, Any]:
        """
        Prepare data for storage in Firestore.

        Converts any FireObjects in _data back to DocumentReferences.
        This is needed because __getattr__ may have cached FireObjects in _data.

        Returns:
            Dictionary with all values converted to Firestore-compatible types.
        """
        prepared = {}
        for key, value in self._data.items():
            prepared[key] = self._convert_value_for_storage(value)
        return prepared

    def _mark_dirty(self) -> None:
        """Mark object as dirty (has unsaved changes).

        Note: In Phase 2, this is a fallback for cases where we don't know
        which specific fields changed. Prefer tracking specific fields when possible.
        """
        # Add all current fields to dirty set as a fallback
        self._dirty_fields.update(self._data.keys())

    def _transition_to_loaded(self, data: Dict[str, Any]) -> None:
        """
        Transition to LOADED state with given data.

        Args:
            data: Document data dictionary.
        """
        object.__setattr__(self, '_data', data)
        object.__setattr__(self, '_state', State.LOADED)
        # Clear dirty tracking (Phase 2: field-level tracking)
        self._dirty_fields.clear()
        self._deleted_fields.clear()
        self._atomic_ops.clear()

    def _transition_to_deleted(self) -> None:
        """Transition to DELETED state."""
        object.__setattr__(self, '_state', State.DELETED)

    def _sync_client_for_materialization(self) -> Optional[Any]:
        """Return the sync client used for nested conversions, if any."""

        if hasattr(self, '_sync_client') and self._sync_client:
            return self._sync_client
        if hasattr(self, '_sync_doc_ref') and self._sync_doc_ref:
            return self._sync_doc_ref._client
        return None

    # =========================================================================
    # Firestore I/O Hooks (Implemented by subclasses)
    # =========================================================================

    def _get_snapshot(self, transaction: Optional[Any] = None) -> Any:
        """Retrieve a DocumentSnapshot for this object.

        Concrete subclasses must implement this to perform the appropriate
        Firestore client operation (sync or async) and return the resulting
        snapshot object.
        """

        raise NotImplementedError("Subclasses must implement _get_snapshot()")

    def _create_document(self, doc_id: Optional[str] = None) -> Any:
        """Create a new document reference for DETACHED objects.

        Returns a client-specific document reference that should be used for
        initial writes when saving a DETACHED object.
        """

        raise NotImplementedError("Subclasses must implement _create_document()")

    def _write_set(
        self,
        doc_ref: Any,
        data: Dict[str, Any],
        transaction: Optional[Any] = None,
        batch: Optional[Any] = None,
    ) -> Any:
        """Write a full document replacement to Firestore."""

        raise NotImplementedError("Subclasses must implement _write_set()")

    def _write_update(
        self,
        update_dict: Dict[str, Any],
        transaction: Optional[Any] = None,
        batch: Optional[Any] = None,
    ) -> Any:
        """Apply a partial update to the backing document."""

        raise NotImplementedError("Subclasses must implement _write_update()")

    def _write_delete(self, batch: Optional[Any] = None) -> Any:
        """Delete the backing Firestore document."""

        raise NotImplementedError("Subclasses must implement _write_delete()")

    # =========================================================================
    # Shared lifecycle helpers
    # =========================================================================

    def _should_skip_fetch(self, force: bool) -> bool:
        """Validate state and determine if fetch work can be skipped."""

        self._validate_not_detached("fetch()")
        self._validate_not_deleted("fetch()")
        return self._state == State.LOADED and not force

    def _finalize_fetch_from_snapshot(self, snapshot: DocumentSnapshot) -> 'BaseFireObject':
        """Populate internal state from a Firestore snapshot."""

        if not snapshot.exists:
            path = getattr(self._doc_ref, 'path', 'unknown-document')
            raise NotFound(f"Document {path} does not exist")

        data = snapshot.to_dict() or {}
        converted_data = {}
        sync_client = self._sync_client_for_materialization()
        is_async = self._is_async_context()
        for key, value in data.items():
            converted_data[key] = self._convert_snapshot_value_for_retrieval(
                value,
                is_async=is_async,
                sync_client=sync_client,
            )

        self._transition_to_loaded(converted_data)
        return self

    def _build_update_dict(self) -> Dict[str, Any]:
        """Create the minimal payload for partial updates."""

        update_dict: Dict[str, Any] = {}

        for field in self._dirty_fields:
            update_dict[field] = self._convert_value_for_storage(self._data[field])

        for field in self._deleted_fields:
            update_dict[field] = firestore.DELETE_FIELD

        for field, operation in self._atomic_ops.items():
            update_dict[field] = operation

        return update_dict

    def _build_save_plan(
        self,
        doc_id: Optional[str],
        transaction: Optional[Any],
        batch: Optional[Any],
    ) -> _SavePlan:
        """Determine the write operation required for ``save``."""

        self._validate_not_deleted("save()")

        if self._state == State.DETACHED:
            if transaction is not None:
                raise ValueError(
                    "Cannot create new documents (DETACHED -> LOADED) within a transaction. "
                    "Create the document first, then use transactions for updates."
                )
            if batch is not None:
                raise ValueError(
                    "Cannot create new documents (DETACHED -> LOADED) within a batch. "
                    "Create the document first, then use batches for updates."
                )

            doc_ref = self._create_document(doc_id)
            storage_data = self._prepare_data_for_storage()
            return _SavePlan(_SaveAction.CREATE, doc_ref=doc_ref, payload=storage_data)

        if self._state == State.ATTACHED:
            storage_data = self._prepare_data_for_storage()
            return _SavePlan(_SaveAction.SET, doc_ref=self._doc_ref, payload=storage_data)

        if self._state == State.LOADED:
            if not self.is_dirty():
                return _SavePlan(_SaveAction.NOOP)

            update_dict = self._build_update_dict()
            return _SavePlan(_SaveAction.UPDATE, doc_ref=self._doc_ref, payload=update_dict)

        return _SavePlan(_SaveAction.NOOP)

    def _execute_save_plan_sync(
        self,
        plan: _SavePlan,
        transaction: Optional[Any],
        batch: Optional[Any],
    ) -> None:
        """Perform a save according to ``plan`` for synchronous subclasses."""

        if plan.action is _SaveAction.NOOP:
            return

        if plan.action is _SaveAction.CREATE:
            self._write_set(plan.doc_ref, plan.payload or {}, transaction, batch)
            object.__setattr__(self, '_doc_ref', plan.doc_ref)
            self._transition_to_loaded(self._data)
            return

        if plan.action is _SaveAction.SET:
            self._write_set(plan.doc_ref, plan.payload or {}, transaction, batch)
            object.__setattr__(self, '_state', State.LOADED)
            self._mark_clean()
            return

        if plan.action is _SaveAction.UPDATE:
            self._write_update(plan.payload or {}, transaction, batch)
            self._mark_clean()

    async def _execute_save_plan_async(
        self,
        plan: _SavePlan,
        transaction: Optional[Any],
        batch: Optional[Any],
    ) -> None:
        """Perform a save according to ``plan`` for async subclasses."""

        if plan.action is _SaveAction.NOOP:
            return

        if plan.action is _SaveAction.CREATE:
            await self._write_set(plan.doc_ref, plan.payload or {}, transaction, batch)
            object.__setattr__(self, '_doc_ref', plan.doc_ref)
            self._transition_to_loaded(self._data)
            return

        if plan.action is _SaveAction.SET:
            await self._write_set(plan.doc_ref, plan.payload or {}, transaction, batch)
            object.__setattr__(self, '_state', State.LOADED)
            self._mark_clean()
            return

        if plan.action is _SaveAction.UPDATE:
            await self._write_update(plan.payload or {}, transaction, batch)
            self._mark_clean()

    def _delete_sync(self, batch: Optional[Any] = None) -> None:
        """Shared delete logic for synchronous subclasses."""

        self._validate_not_detached("delete()")
        self._validate_not_deleted("delete()")
        self._write_delete(batch=batch)
        self._transition_to_deleted()

    async def _delete_async(self, batch: Optional[Any] = None) -> None:
        """Shared delete logic for async subclasses."""

        self._validate_not_detached("delete()")
        self._validate_not_deleted("delete()")
        await self._write_delete(batch=batch)
        self._transition_to_deleted()

    def _materialize_field(self, name: str) -> Any:
        """Return a field value with conversions applied and cached."""

        if name not in self._data:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        value = self._data[name]
        converted = self._convert_snapshot_value_for_retrieval(
            value,
            is_async=self._is_async_context(),
            sync_client=self._sync_client_for_materialization(),
        )

        # Cache converted value if changed
        if converted is not value:
            self._data[name] = converted

        return converted

    # =========================================================================
    # Real-Time Listeners (Sync-only via _sync_doc_ref or _doc_ref)
    # =========================================================================

    def on_snapshot(self, callback: Any) -> Any:
        """
        Listen for real-time updates to this document.

        This method sets up a real-time listener that fires the callback
        whenever the document changes in Firestore. The listener runs on
        a separate thread managed by the Firestore SDK.

        **Important**: This is a sync-only feature. Even for AsyncFireObject
        instances, the listener uses the synchronous client (via _sync_doc_ref)
        to run on a background thread. This is the standard Firestore pattern
        for real-time listeners in Python.

        Args:
            callback: Callback function invoked on document changes.
                     Signature: callback(doc_snapshot, changes, read_time)
                     - doc_snapshot: List of DocumentSnapshot objects
                     - changes: List of DocumentChange objects
                     - read_time: Timestamp of the snapshot

        Returns:
            Watch object with an `.unsubscribe()` method to stop listening.

        Raises:
            ValueError: If called on a DETACHED object (no document path).
            RuntimeError: If called on a DELETED object.

        Example:
            import threading

            # Create event for synchronization
            callback_done = threading.Event()

            def on_change(doc_snapshot, changes, read_time):
                for doc in doc_snapshot:
                    print(f"Document updated: {doc.to_dict()}")
                callback_done.set()

            # Start listening
            user = db.doc('users/alice')
            watch = user.on_snapshot(on_change)

            # Wait for initial snapshot
            callback_done.wait()

            # Later: stop listening
            watch.unsubscribe()

        Note:
            The callback runs on a separate thread. Use threading primitives
            (Event, Lock, Queue) for synchronization with your main thread.
        """
        self._validate_not_detached("on_snapshot()")
        self._validate_not_deleted("on_snapshot()")

        # For sync FireObject, use _doc_ref directly
        # For async FireObject, use _sync_doc_ref (always available)
        if hasattr(self, '_sync_doc_ref') and self._sync_doc_ref is not None:
            # AsyncFireObject: use sync doc ref for listener
            doc_ref = self._sync_doc_ref
        else:
            # FireObject: use regular doc ref
            doc_ref = self._doc_ref

        # Set up the listener
        return doc_ref.on_snapshot(callback)

    def _is_async_context(self) -> bool:
        """
        Determine if this FireObject is in an async context.

        Returns:
            True if this is an AsyncFireObject, False if sync FireObject.

        Example:
            if self._is_async_context():
                # Use async patterns
            else:
                # Use sync patterns
        """
        # Check if we have a doc_ref and if it's async
        if self._doc_ref is not None:
            return 'Async' in self._doc_ref.__class__.__name__

        # Fall back to checking the class name
        return 'Async' in self.__class__.__name__

    def _convert_value_for_storage(self, value: Any) -> Any:
        """
        Convert a value for storage in Firestore, handling special types.

        Recursively processes values to convert:
        - FireObject/AsyncFireObject → DocumentReference
        - FireVector → native Vector
        - DocumentReference → pass through (allow raw refs)
        - Lists → recursively process items
        - Dicts → recursively process values

        Args:
            value: The value to convert.

        Returns:
            The converted value ready for Firestore storage.

        Raises:
            ValueError: If trying to store a DETACHED FireObject.
            TypeError: If trying to mix sync and async FireObjects.

        Example:
            # Assign a FireObject reference
            post.author = user  # user is a FireObject
            # Internally converts to DocumentReference
        """
        # Handle FireObject/AsyncFireObject → DocumentReference
        if isinstance(value, BaseFireObject):
            # Validate not DETACHED
            if value._state == State.DETACHED:
                raise ValueError(
                    "Cannot assign a DETACHED FireObject as a reference. "
                    "The object must be saved first to have a document path."
                )

            # Validate type compatibility (sync vs async)
            is_async = self._is_async_context()
            value_is_async = value._is_async_context()

            if is_async != value_is_async:
                raise TypeError(
                    f"Cannot assign {'async' if value_is_async else 'sync'} FireObject "
                    f"to {'async' if is_async else 'sync'} FireObject. "
                    "Both objects must be from the same context (sync or async)."
                )

            # Convert to DocumentReference
            return value._doc_ref

        # Handle FireVector → native Vector
        from .fire_vector import FireVector
        if isinstance(value, FireVector):
            return value.to_firestore_vector()

        # Handle DocumentReference → pass through (allow raw refs)
        if isinstance(value, (DocumentReference, AsyncDocumentReference)):
            return value

        # Handle lists → recursively convert items
        if isinstance(value, list):
            return [self._convert_value_for_storage(item) for item in value]

        # Handle dicts → recursively convert values
        if isinstance(value, dict):
            return {k: self._convert_value_for_storage(v) for k, v in value.items()}

        # Everything else passes through unchanged
        return value

    @classmethod
    def _convert_snapshot_value_for_retrieval(
        cls,
        value: Any,
        is_async: bool,
        sync_client: Optional[Any] = None
    ) -> Any:
        """
        Convert a value from Firestore snapshot for Python use.

        Recursively processes values to convert:
        - DocumentReference → FireObject/AsyncFireObject (ATTACHED state)
        - native Vector → FireVector
        - Lists → recursively process items
        - Dicts → recursively process values

        Args:
            value: The value from Firestore snapshot.
            is_async: Whether to create async or sync FireObjects.
            sync_client: Optional sync Firestore client for async lazy loading.

        Returns:
            The converted value ready for Python use.

        Example:
            # Reading a document with a reference field
            doc.fetch()
            author = doc.author  # Automatically converted to FireObject
        """
        # Handle DocumentReference → FireObject/AsyncFireObject
        if isinstance(value, (DocumentReference, AsyncDocumentReference)):
            if is_async:
                from .async_fire_object import AsyncFireObject
                # For async, provide sync_doc_ref for lazy loading
                sync_ref = None
                if isinstance(value, DocumentReference):
                    # It's already a sync ref
                    sync_ref = value
                elif isinstance(value, AsyncDocumentReference) and sync_client:
                    # Create sync ref from async ref using sync_client
                    sync_ref = sync_client.document(value.path)

                return AsyncFireObject(
                    doc_ref=value,
                    initial_state=State.ATTACHED,
                    sync_doc_ref=sync_ref,
                    sync_client=sync_client
                )
            else:
                from .fire_object import FireObject
                return FireObject(doc_ref=value, initial_state=State.ATTACHED)

        # Handle native Vector → FireVector
        if isinstance(value, Vector):
            from .fire_vector import FireVector
            return FireVector.from_firestore_vector(value)

        # Handle lists → recursively convert items
        if isinstance(value, list):
            return [cls._convert_snapshot_value_for_retrieval(item, is_async, sync_client) for item in value]

        # Handle dicts → recursively convert values
        if isinstance(value, dict):
            return {k: cls._convert_snapshot_value_for_retrieval(v, is_async, sync_client) for k, v in value.items()}

        # Everything else passes through unchanged
        return value

    @classmethod
    def _create_from_snapshot_base(
        cls,
        snapshot: DocumentSnapshot,
        parent_collection: Optional[Any] = None,
        sync_client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Extract data for creating FireObject from snapshot.

        This is shared logic for from_snapshot() factory methods.

        Args:
            snapshot: DocumentSnapshot from native API.
            parent_collection: Optional parent collection reference.
            sync_client: Optional sync Firestore client for async lazy loading.

        Returns:
            Dictionary with initialization parameters.

        Raises:
            ValueError: If snapshot doesn't exist.
        """
        if not snapshot.exists:
            raise ValueError("Cannot create FireObject from non-existent snapshot")

        # Get data from snapshot
        data = snapshot.to_dict() or {}

        # Detect async context from snapshot reference
        is_async = 'Async' in snapshot.reference.__class__.__name__

        # Convert all values (DocumentReference → FireObject, Vector → FireVector, etc.)
        converted_data = {}
        for key, value in data.items():
            converted_data[key] = cls._convert_snapshot_value_for_retrieval(value, is_async, sync_client)

        return {
            'doc_ref': snapshot.reference,
            'initial_state': State.LOADED,
            'parent_collection': parent_collection,
            'data': converted_data
        }
