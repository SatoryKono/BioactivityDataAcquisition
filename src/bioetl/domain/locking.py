"""Lock context for passing lock state through layers.

Implements RULES.md §3.3 - Writers MUST verify lock held before write.

This module provides:
- FencingToken: Monotonically increasing token issued on lock acquisition
- LockContext: Immutable value object representing a held lock
- LockContextHolder: Mutable holder for sharing lock context between components
- LockNotHeldError: Exception raised when write attempted without lock
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.constants import DEFAULT_LOCK_TTL_SECONDS

if TYPE_CHECKING:
    from bioetl.domain.types import RunID

__all__ = [
    "FencingToken",
    "LockContext",
    "LockContextHolder",
    "LockNotHeldError",
]


@dataclass(frozen=True, slots=True)
class FencingToken:
    """Monotonically increasing token issued on lock acquisition.

    Each successful acquire() returns a token with a higher sequence number
    than any previous token for that key. Writers can compare tokens to
    detect stale lock holders.

    For MemoryLock (ADR-010): trivial implementation over owner_id + counter.

    Attributes:
        sequence: Monotonically increasing counter per lock key.
        key: The lock key this token was issued for.
        owner_id: RunID of the owner who acquired the lock.
        issued_at: Monotonic timestamp when the token was issued.
    """

    sequence: int
    key: str
    owner_id: RunID
    issued_at: float


class LockNotHeldError(Exception):
    """Raised when write operation attempted without valid lock.

    This exception indicates a programming error - the caller forgot
    to acquire a lock before attempting a write operation.
    """

    def __init__(self, operation: str, expected_key: str) -> None:
        """Initialize LockNotHeldError.

        Args:
            operation: The operation that was attempted (e.g., "write_silver").
            expected_key: The lock key that should have been held.
        """
        self.operation = operation
        self.expected_key = expected_key
        super().__init__(
            f"Cannot perform {operation}: lock '{expected_key}' not held. "
            "Acquire a runtime lock before write operations."
        )


@dataclass(frozen=True)
class LockContext:
    """Immutable context representing a held lock.

    Passed from application layer to infrastructure layer
    to verify lock is held before write operations.

    This is a Value Object - immutable and compared by value.

    Attributes:
        key: The lock key (e.g., "lock:chembl_activity").
        owner_id: RunID that acquired the lock.
        exclusive: True for backfill/rebuild operations.
        acquired_at: Monotonic timestamp when lock was acquired (for TTL checks).
        fencing_token: Token issued by LockPort.acquire() for fencing validation.
    """

    key: str
    owner_id: RunID
    exclusive: bool = False
    acquired_at: float | None = None
    fencing_token: FencingToken | None = None

    @classmethod
    def create(
        cls,
        provider: str,
        entity: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> LockContext:
        """Create lock context with standard key format.

        Args:
            provider: Provider name (e.g., "chembl").
            entity: Entity name (e.g., "activity").
            owner_id: RunID that acquired the lock.
            exclusive: True for backfill/rebuild (uses :exclusive suffix).

        Returns:
            LockContext with properly formatted key.
        """
        key = (
            f"lock:{provider}_{entity}:exclusive"
            if exclusive
            else f"lock:{provider}_{entity}"
        )

        return cls(
            key=key,
            owner_id=owner_id,
            exclusive=exclusive,
            acquired_at=time.monotonic(),
        )

    def is_valid(self, ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS) -> bool:
        """Check if lock context is still valid (not expired).

        Args:
            ttl_seconds: Maximum age in seconds before lock is considered expired.
                        Default is 1 hour.

        Returns:
            True if lock is still valid, False if expired.
        """
        if self.acquired_at is None:
            return True  # No TTL tracking, assume valid

        elapsed = time.monotonic() - self.acquired_at
        return elapsed < ttl_seconds

    def matches_table(self, table_name: str) -> bool:
        """Check if this lock context matches the given table name.

        Args:
            table_name: Table name in format "provider_entity" (e.g., "chembl_activity").

        Returns:
            True if lock key matches table name.
        """
        # Extract expected key from table name
        expected_key = f"lock:{table_name}"
        exclusive_key = f"lock:{table_name}:exclusive"

        return self.key in (expected_key, exclusive_key)


class LockContextHolder:
    """Mutable holder for sharing lock context between components.

    Used to pass lock context from the runtime lock owner
    to writers (which need to verify lock is held).

    Thread-safe for single-writer, multiple-reader scenarios.

    Example:
        >>> holder = LockContextHolder()
        >>> # Runtime lock owner sets context after acquiring lock
        >>> holder.set(LockContext.create("chembl", "activity", run_id))
        >>> # Writers retrieve context when writing
        >>> context = holder.get()
        >>> if context:
        ...     writer.write_bronze(..., lock_context=context)
    """

    __slots__ = ("_context",)

    def __init__(self) -> None:
        """Initialize with no lock context."""
        self._context: LockContext | None = None

    def set(self, context: LockContext) -> None:
        """Set the current lock context.

        Called by the runtime lock owner after successfully acquiring a lock.

        Args:
            context: The acquired lock context.
        """
        self._context = context

    def get(self) -> LockContext | None:
        """Get the current lock context.

        Called by writers to verify lock is held.

        Returns:
            Current LockContext if lock is held, None otherwise.
        """
        return self._context

    def clear(self) -> None:
        """Clear the lock context.

        Called by the runtime lock owner after releasing the lock.
        """
        self._context = None
