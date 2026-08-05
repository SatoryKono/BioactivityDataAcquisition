# Host attrs/methods provided by concrete composition.
"""Delta Lake specific infrastructure exceptions."""

from __future__ import annotations

from typing import cast

from bioetl.domain.exceptions.storage._storage import (
    StorageError,
    StorageQuotaExceededError,
)
from bioetl.domain.types import ErrorType


def delta_write_conflict_error(
    table_path: str,
    operation: str = "write",
    conflicting_version: int | None = None,
) -> StorageError:
    """Compatibility constructor for legacy DeltaWriteConflictError.

    Args:
        table_path: Path to the Delta table where the conflict occurred.
        operation: Operation that caused the conflict; defaults to 'write'.
        conflicting_version: Optional Delta table version that conflicted;
            defaults to None.

    Returns:
        StorageError with NETWORK_ERROR type and conflict context attached.
    """
    msg = f"Delta write conflict on '{table_path}' during {operation}"
    if conflicting_version is not None:
        msg += f" (conflicting version: {conflicting_version})"
    error = StorageError(msg)
    error = cast(
        StorageError,
        error.with_context(
            table_path=table_path,
            operation=operation,
            conflicting_version=conflicting_version,
        ),
    )
    object.__setattr__(error, "error_type", ErrorType.NETWORK_ERROR)
    return error


DeltaTransactionError = StorageQuotaExceededError


def _format_column_diff(
    expected_columns: list[str],
    actual_columns: list[str],
) -> list[str]:
    """Format missing and extra columns as message parts."""
    parts: list[str] = []
    missing = set(expected_columns) - set(actual_columns)
    extra = set(actual_columns) - set(expected_columns)
    if missing:
        parts.append(f"missing columns: {sorted(missing)}")
    if extra:
        parts.append(f"unexpected columns: {sorted(extra)}")
    return parts


def _format_type_mismatches(
    type_mismatches: dict[str, tuple[str, str]],
) -> str:
    """Format type mismatches as a message part."""
    mismatches = [
        f"{col}: expected {exp}, got {act}"
        for col, (exp, act) in type_mismatches.items()
    ]
    return f"type mismatches: [{', '.join(mismatches)}]"


def _build_schema_validation_message(
    table_path: str,
    expected_columns: list[str],
    actual_columns: list[str],
    type_mismatches: dict[str, tuple[str, str]],
) -> str:
    """Build error message for schema validation error."""
    parts = [f"Schema validation failed for '{table_path}'"]

    if expected_columns and actual_columns:
        parts.extend(_format_column_diff(expected_columns, actual_columns))

    if type_mismatches:
        parts.append(_format_type_mismatches(type_mismatches))

    return ", ".join(parts)


def delta_schema_validation_error(
    table_path: str,
    expected_columns: list[str] | None = None,
    actual_columns: list[str] | None = None,
    type_mismatches: dict[str, tuple[str, str]] | None = None,
) -> StorageQuotaExceededError:
    """Compatibility constructor for legacy DeltaSchemaValidationError.

    Args:
        table_path: Path to the Delta table with schema mismatch.
        expected_columns: Expected column names; defaults to None.
        actual_columns: Actual column names found in the table; defaults to None.
        type_mismatches: Dict mapping column names to (expected_type, actual_type)
            tuples; defaults to None.

    Returns:
        StorageQuotaExceededError with SCHEMA_MISMATCH_GOLD type and diff context.
    """
    expected = expected_columns or []
    actual = actual_columns or []
    mismatches = type_mismatches or {}
    message = _build_schema_validation_message(
        table_path=table_path,
        expected_columns=expected,
        actual_columns=actual,
        type_mismatches=mismatches,
    )
    error = StorageQuotaExceededError(path=table_path)
    error.args = (message,)
    error = cast(
        StorageQuotaExceededError,
        error.with_context(
            table_path=table_path,
            expected_columns=expected,
            actual_columns=actual,
            type_mismatches=mismatches,
        ),
    )
    object.__setattr__(error, "error_type", ErrorType.SCHEMA_MISMATCH_GOLD)
    return error


def delta_optimize_error(
    table_path: str,
    operation: str,
    reason: str,
) -> StorageError:
    """Compatibility constructor for legacy DeltaOptimizeError.

    Args:
        table_path: Path to the Delta table where the operation failed.
        operation: Name of the failed Delta operation (e.g., 'optimize', 'vacuum').
        reason: Human-readable description of why the operation failed.

    Returns:
        StorageError with NETWORK_ERROR type and operation context attached.
    """
    error = StorageError(f"Delta {operation} failed on '{table_path}': {reason}")
    error = cast(
        StorageError,
        error.with_context(
            table_path=table_path,
            operation=operation,
            reason=reason,
        ),
    )
    object.__setattr__(error, "error_type", ErrorType.NETWORK_ERROR)
    return error


DeltaWriteConflictError = delta_write_conflict_error
DeltaSchemaValidationError = delta_schema_validation_error
DeltaOptimizeError = delta_optimize_error
