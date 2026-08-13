"""Source-metadata exception tuple for batch runtime metadata resolution."""

from __future__ import annotations

from bioetl.application.core.batch_operation_errors import OPERATION_ERRORS

SOURCE_METADATA_ERRORS: tuple[type[Exception], ...] = (
    *OPERATION_ERRORS,
    AttributeError,
)

__all__ = ["SOURCE_METADATA_ERRORS"]
