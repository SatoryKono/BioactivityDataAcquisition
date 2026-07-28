"""Operation-level exception tuple shared by batch runtime helpers."""

from __future__ import annotations

from bioetl.domain.exceptions import BioETLError

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
    """Return the stable telemetry type name for a batch operation error."""
    return type(exc).__name__

__all__ = [
    "OPERATION_ERRORS",
    "OperationErrorTypes",
    "is_operation_error",
    "operation_error_type_name",
]
