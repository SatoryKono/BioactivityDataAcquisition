"""Shared exception policy for application batch operations."""

from __future__ import annotations

from bioetl.domain.exceptions import BioETLError

__all__ = [
    "OPERATION_ERRORS",
    "OperationErrorTypes",
    "is_operation_error",
    "operation_error_type_name",
]

OperationErrorTypes = tuple[type[Exception], ...]

OPERATION_ERRORS: OperationErrorTypes = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


def is_operation_error(exc: BaseException) -> bool:
    """Return whether an exception belongs to the batch operation policy."""
    return isinstance(exc, OPERATION_ERRORS)


def operation_error_type_name(exc: BaseException) -> str:
    """Return the stable telemetry type name for an operation error."""
    return type(exc).__name__
