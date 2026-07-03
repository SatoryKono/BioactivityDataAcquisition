"""Shared runtime failure tuples for adjacent batch-processing families."""

from __future__ import annotations

__all__ = [
    "OPERATION_ERRORS",
    "PIPELINE_EXECUTION_ERRORS",
    "SOURCE_METADATA_ERRORS",
]

from bioetl.domain.exceptions import BioETLError

OPERATION_ERRORS = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)

PIPELINE_EXECUTION_ERRORS = (
    *OPERATION_ERRORS,
    KeyError,
    AttributeError,
)

SOURCE_METADATA_ERRORS = (
    *OPERATION_ERRORS,
    AttributeError,
)
