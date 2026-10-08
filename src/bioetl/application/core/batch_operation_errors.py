"""Compatibility re-exports for the application batch-operation error policy."""

from __future__ import annotations

from bioetl.application.batch_operation_errors import (
    OPERATION_ERRORS,
    OperationErrorTypes,
)
from bioetl.application.batch_operation_errors import (
    is_operation_error as _is_operation_error,
)
from bioetl.application.batch_operation_errors import (
    operation_error_type_name as _operation_error_type_name,
)


def is_operation_error(exc: BaseException) -> bool:
    """Compatibility wrapper for the application-level error policy."""
    return _is_operation_error(exc)


def operation_error_type_name(exc: BaseException) -> str:
    """Compatibility wrapper for the application-level error policy."""
    return _operation_error_type_name(exc)

__all__ = [
    "OPERATION_ERRORS",
    "OperationErrorTypes",
    "is_operation_error",
    "operation_error_type_name",
]
