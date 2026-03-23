"""Shared runtime failure tuples for adjacent batch-processing families."""

from __future__ import annotations

__all__ = [
    "PIPELINE_EXECUTION_ERRORS",
    "SOURCE_METADATA_ERRORS",
]

from bioetl.domain.exceptions import BioETLError

PIPELINE_EXECUTION_ERRORS = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
)

SOURCE_METADATA_ERRORS = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    AttributeError,
)
