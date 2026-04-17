"""Compatibility facade for the canonical execution seam.

The canonical implementation binds correlation fields through
``context.log_correlation_fields()`` and ultimately performs
``self.logger.bind(**context.log_correlation_fields())`` in the execution
package. This facade intentionally preserves that public contract while
re-exporting the canonical service.
"""

from __future__ import annotations

from bioetl.application.services.execution.pipeline_runner_service import (
    PipelineNotFoundError,
    PipelineRunnerService,
    PipelineRunResult,
    RunOptions,
    RunResult,
)

__all__ = [
    "PipelineNotFoundError",
    "PipelineRunResult",
    "PipelineRunnerService",
    "RunOptions",
    "RunResult",
]
