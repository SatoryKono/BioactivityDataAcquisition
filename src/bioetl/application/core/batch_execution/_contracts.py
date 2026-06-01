"""Backward-compatible re-export for `bioetl.application.core.batch_execution.contracts`."""

from __future__ import annotations

from bioetl.application.core.batch_execution import contracts as _public

BatchExecutionCountersSnapshot = _public.BatchExecutionCountersSnapshot
BatchExecutionMemoryState = _public.BatchExecutionMemoryState
BatchExecutionStateProtocol = _public.BatchExecutionStateProtocol
BatchExecutionStatisticsState = _public.BatchExecutionStatisticsState
BatchResultBuilderProtocol = _public.BatchResultBuilderProtocol

__all__ = [
    "BatchExecutionCountersSnapshot",
    "BatchExecutionMemoryState",
    "BatchExecutionStateProtocol",
    "BatchExecutionStatisticsState",
    "BatchResultBuilderProtocol",
]
