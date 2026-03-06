"""Delta Lake specific infrastructure exceptions."""

from __future__ import annotations

from bioetl.domain.exceptions.base import CriticalError
from bioetl.domain.exceptions.infrastructure._storage import StorageError
from bioetl.domain.types import ErrorType


class DeltaWriteConflictError(StorageError):
    """Raised when Delta Lake detects a concurrent write conflict."""

    error_type = ErrorType.NETWORK_ERROR

    def __init__(
        self,
        table_path: str,
        operation: str = "write",
        conflicting_version: int | None = None,
    ) -> None:
        self.table_path = table_path
        self.operation = operation
        self.conflicting_version = conflicting_version
        msg = f"Delta write conflict on '{table_path}' during {operation}"
        if conflicting_version is not None:
            msg += f" (conflicting version: {conflicting_version})"
        super().__init__(msg)


class DeltaTransactionError(CriticalError):
    """Raised when Delta Lake transaction fails to commit."""

    error_type = ErrorType.DB_UNAVAILABLE

    def __init__(
        self,
        table_path: str,
        reason: str,
        version: int | None = None,
    ) -> None:
        self.table_path = table_path
        self.reason = reason
        self.version = version
        msg = f"Delta transaction failed on '{table_path}': {reason}"
        if version is not None:
            msg += f" (version: {version})"
        super().__init__(msg)


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


class DeltaSchemaValidationError(CriticalError):
    """Raised when schema validation fails during Delta write."""

    error_type = ErrorType.SCHEMA_MISMATCH_GOLD

    def __init__(
        self,
        table_path: str,
        expected_columns: list[str] | None = None,
        actual_columns: list[str] | None = None,
        type_mismatches: dict[str, tuple[str, str]] | None = None,
    ) -> None:
        self.table_path = table_path
        self.expected_columns = expected_columns or []
        self.actual_columns = actual_columns or []
        self.type_mismatches = type_mismatches or {}

        super().__init__(
            _build_schema_validation_message(
                table_path,
                self.expected_columns,
                self.actual_columns,
                self.type_mismatches,
            )
        )


class DeltaOptimizeError(StorageError):
    """Raised when Delta VACUUM or OPTIMIZE operation fails."""

    error_type = ErrorType.NETWORK_ERROR

    def __init__(
        self,
        table_path: str,
        operation: str,
        reason: str,
    ) -> None:
        self.table_path = table_path
        self.operation = operation
        self.reason = reason
        super().__init__(f"Delta {operation} failed on '{table_path}': {reason}")
