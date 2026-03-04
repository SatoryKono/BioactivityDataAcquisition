"""Shared exception groups for CompositePipelineRunner."""

from __future__ import annotations

__all__ = [
    "CHECKPOINT_NON_FATAL_ERRORS",
    "DQ_REPORT_NON_FATAL_ERRORS",
    "PIPELINE_EXECUTION_ERRORS",
    "QUARANTINE_WRITE_NON_FATAL_ERRORS",
]


from bioetl.domain.exceptions import (
    CheckpointConflictError,
    DataQualityError,
    NetworkError,
    StorageError,
)

CHECKPOINT_NON_FATAL_ERRORS = (
    CheckpointConflictError,
    StorageError,
    OSError,
    ValueError,
    TypeError,
)

PIPELINE_EXECUTION_ERRORS = (
    NetworkError,
    StorageError,
    CheckpointConflictError,
    DataQualityError,
    RuntimeError,
    ValueError,
    TypeError,
    OSError,
)

DQ_REPORT_NON_FATAL_ERRORS = (
    DataQualityError,
    StorageError,
    ImportError,
    ModuleNotFoundError,
    RuntimeError,
    ValueError,
    TypeError,
    OSError,
)

QUARANTINE_WRITE_NON_FATAL_ERRORS = (
    StorageError,
    DataQualityError,
    OSError,
    ValueError,
    TypeError,
)
