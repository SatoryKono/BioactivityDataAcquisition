"""Shared runtime failure tuples for adjacent batch-processing families."""

from __future__ import annotations

__all__ = [
    "OPERATION_ERRORS",
    "PIPELINE_EXECUTION_ERRORS",
    "SOURCE_METADATA_ERRORS",
]

from bioetl.application.core.batch_operation_errors import OPERATION_ERRORS

PIPELINE_EXECUTION_ERRORS: tuple[type[Exception], ...] = (
    *OPERATION_ERRORS,
    KeyError,
    AttributeError,
)

SOURCE_METADATA_ERRORS: tuple[type[Exception], ...] = (
    *OPERATION_ERRORS,
    AttributeError,
)
