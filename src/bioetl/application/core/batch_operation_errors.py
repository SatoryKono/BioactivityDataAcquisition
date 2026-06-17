"""Operation-level exception tuple shared by batch runtime helpers."""

from __future__ import annotations

from bioetl.domain.exceptions import BioETLError

OPERATION_ERRORS = (
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)

__all__ = ["OPERATION_ERRORS"]
