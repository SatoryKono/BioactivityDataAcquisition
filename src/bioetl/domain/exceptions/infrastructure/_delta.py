"""Delta Lake specific infrastructure exceptions."""

from __future__ import annotations

from bioetl.domain.exceptions.infrastructure._storage import (
    StorageError,
    StorageQuotaExceededError,
)
from bioetl.domain.types import ErrorType


def DeltaWriteConflictError(
    table_path: str,
    operation: str = "write",
    conflicting_version: int | None = None,
) -> StorageError:
    """Compatibility constructor for legacy DeltaWriteConflictError."""
    msg = f"Delta write conflict on '{table_path}' during {operation}"
    if conflicting_version is not None:
        msg += f" (conflicting version: {conflicting_version})"
    error = StorageError(msg)
    error.table_path = table_path
    error.operation = operation
    error.conflicting_version = conflicting_version
    error.error_type = ErrorType.NETWORK_ERROR
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


def DeltaSchemaValidationError(
    table_path: str,
    expected_columns: list[str] | None = None,
    actual_columns: list[str] | None = None,
    type_mismatches: dict[str, tuple[str, str]] | None = None,
) -> StorageQuotaExceededError:
    """Compatibility constructor for legacy DeltaSchemaValidationError."""
    expected = expected_columns or []
    actual = actual_columns or []
    mismatches = type_mismatches or {}
    error = StorageQuotaExceededError(path=table_path)
    error.table_path = table_path
    error.expected_columns = expected
    error.actual_columns = actual
    error.type_mismatches = mismatches
    error.error_type = ErrorType.SCHEMA_MISMATCH_GOLD
    error.args = (
        _build_schema_validation_message(
            table_path=table_path,
            expected_columns=expected,
            actual_columns=actual,
            type_mismatches=mismatches,
        ),
    )
    return error


def DeltaOptimizeError(
    table_path: str,
    operation: str,
    reason: str,
) -> StorageError:
    """Compatibility constructor for legacy DeltaOptimizeError."""
    error = StorageError(f"Delta {operation} failed on '{table_path}': {reason}")
    error.table_path = table_path
    error.operation = operation
    error.reason = reason
    error.error_type = ErrorType.NETWORK_ERROR
    return error
