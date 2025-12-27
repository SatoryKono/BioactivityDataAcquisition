"""Lock context for passing lock state through layers.

Implements RULES.md §3.3 - Writers MUST verify lock held before write.

This module provides:
- LockContext: Immutable value object representing a held lock
- LockNotHeldError: Exception raised when write attempted without lock
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.types import RunID


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
            "Acquire lock via LockManager before write operations."
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
    """

    key: str
    owner_id: RunID
    exclusive: bool = False
    acquired_at: float | None = None

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
        if exclusive:
            key = f"lock:{provider}_{entity}:exclusive"
        else:
            key = f"lock:{provider}_{entity}"

        return cls(
            key=key,
            owner_id=owner_id,
            exclusive=exclusive,
            acquired_at=time.monotonic(),
        )

    def is_valid(self, ttl_seconds: int = 3600) -> bool:
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
