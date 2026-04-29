"""Public batch-execution contract seam for adjacent application/core modules."""

from __future__ import annotations

from bioetl.application.core.batch_execution._contracts import (
    BatchExecutionStateProtocol,
    BatchResultBuilderProtocol,
)

__all__ = ["BatchExecutionStateProtocol", "BatchResultBuilderProtocol"]
