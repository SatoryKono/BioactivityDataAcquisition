"""Source-metadata exception tuple for batch runtime metadata resolution."""

from __future__ import annotations

from bioetl.application.core.batch_pipeline_execution_errors import (
    PIPELINE_EXECUTION_ERRORS,
)

SOURCE_METADATA_ERRORS: tuple[type[Exception], ...] = (
    *PIPELINE_EXECUTION_ERRORS,
    AttributeError,
)
