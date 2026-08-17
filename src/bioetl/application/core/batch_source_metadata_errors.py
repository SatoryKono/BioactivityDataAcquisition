"""Source-metadata exception tuple for batch runtime metadata resolution."""

from __future__ import annotations

from bioetl.application.core import batch_pipeline_execution_errors as errors

SOURCE_METADATA_ERRORS: tuple[type[Exception], ...] = (
    *errors.PIPELINE_EXECUTION_ERRORS,
    AttributeError,
)

__all__ = ["SOURCE_METADATA_ERRORS"]
