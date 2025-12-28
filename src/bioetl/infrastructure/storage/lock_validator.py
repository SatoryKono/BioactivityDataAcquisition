"""Lock validation utility for storage writers.

Centralizes lock validation logic per RULES.md §3.3 - Writers MUST verify lock held.

This module provides a single source of truth for lock validation used by:
- BronzeWriter
- DeltaWriter (Silver)
- GoldWriter
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.locking import LockContext, LockNotHeldError
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


def _check_lock_present(
    lock_context: LockContext | None,
    operation: str,
    expected_key: str,
    logger: LoggerPort,
    log_context: dict[str, str],
) -> None:
    """Validate lock context is not None."""
    if lock_context is None:
        logger.error("Write attempted without lock", **log_context)
        raise LockNotHeldError(operation, expected_key)


def _check_lock_matches_table(
    lock_context: LockContext,
    table_name: str,
    operation: str,
    expected_key: str,
    logger: LoggerPort,
    log_context: dict[str, str],
) -> None:
    """Validate lock matches the target table."""
    if not lock_context.matches_table(table_name):
        logger.error("Write attempted with wrong lock", actual_key=lock_context.key, **log_context)
        raise LockNotHeldError(f"{operation} (got {lock_context.key})", expected_key)


def _check_lock_valid(
    lock_context: LockContext,
    operation: str,
    expected_key: str,
    logger: LoggerPort,
    log_context: dict[str, str],
) -> None:
    """Validate lock is not expired."""
    if not lock_context.is_valid():
        ctx = {k: v for k, v in log_context.items() if k != "expected_key"}
        logger.error("Write attempted with expired lock", lock_key=lock_context.key, **ctx)
        raise LockNotHeldError(f"{operation} (lock expired)", expected_key)


def _check_owner_id(
    lock_context: LockContext,
    expected_owner_id: RunID | None,
    operation: str,
    expected_key: str,
    logger: LoggerPort,
    log_context: dict[str, str],
) -> None:
    """Validate owner_id matches expected (fencing token)."""
    if expected_owner_id is None or lock_context.owner_id == expected_owner_id:
        return
    ctx = {k: v for k, v in log_context.items() if k != "expected_key"}
    logger.error(
        "Write attempted with wrong owner_id (fencing token mismatch)",
        expected_owner_id=str(expected_owner_id),
        actual_owner_id=str(lock_context.owner_id),
        lock_key=lock_context.key,
        **ctx,
    )
    raise LockNotHeldError(
        f"{operation} (owner mismatch: {lock_context.owner_id} != {expected_owner_id})",
        expected_key,
    )


def validate_lock_for_write(
    *,
    table_name: str,
    lock_context: LockContext | None,
    logger: LoggerPort,
    operation: str,
    require_lock: bool = True,
    expected_owner_id: RunID | None = None,
    log_context: dict[str, str] | None = None,
) -> None:
    """Validate that lock is held before write operation.

    Implements RULES.md §3.3 - Writers MUST verify lock held.

    Args:
        table_name: Target table name (format: "provider_entity").
        lock_context: The lock context from application layer.
        logger: Structured logger for observability.
        operation: Operation name for error messages (e.g., "write_bronze", "write_silver").
        require_lock: If True, validate lock is held. If False, skip validation
                     (e.g., for tests or non-concurrent scenarios).
        expected_owner_id: Expected owner RunID (fencing token). If provided,
                          validates that lock_context.owner_id matches to prevent
                          writes from stale lock holders after lock re-acquisition.
        log_context: Additional context fields for logging (e.g., provider, entity).

    Raises:
        LockNotHeldError: If lock is not held, doesn't match table,
                         is expired, or owner_id doesn't match.
    """
    if not require_lock:
        return  # Lock validation disabled (e.g., for tests)

    expected_key = f"lock:{table_name}"
    base_log_context = {"table": table_name, "expected_key": expected_key}
    if log_context:
        base_log_context.update(log_context)

    _check_lock_present(lock_context, operation, expected_key, logger, base_log_context)
    # At this point lock_context is not None
    assert lock_context is not None  # for type checker
    _check_lock_matches_table(lock_context, table_name, operation, expected_key, logger, base_log_context)
    _check_lock_valid(lock_context, operation, expected_key, logger, base_log_context)
    _check_owner_id(lock_context, expected_owner_id, operation, expected_key, logger, base_log_context)
