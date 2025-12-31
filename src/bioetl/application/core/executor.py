"""Executor module for pipeline batch processing.

This module provides the Executor alias for BatchExecutor, implementing
the mandatory tracing spans for pipeline operations.

The executor is responsible for:
- Orchestrating the complete ETL flow (extract → transform → write)
- Creating tracing spans for all critical operations
- Adaptive batch sizing based on memory pressure
- Graceful shutdown handling
- Checkpoint management

Implements RULES.md §6.2.4 (Tracing Enforcement):
- Root span for pipeline execution
- Nested spans for each batch
- Per-layer spans for transform/write operations

Example:
    >>> from bioetl.application.core.executor import Executor
    >>> executor = Executor(...)
    >>> await executor.execute(limit=1000)
    >>> # Or process individual batches:
    >>> result = await executor.process(records, start_index=0)

"""

from __future__ import annotations

from bioetl.application.core.batch_executor import BatchExecutor, BatchResult

__all__ = ["BatchExecutor", "BatchResult", "Executor", "execute", "process"]

# Executor is an alias for BatchExecutor
# Provides the mandated interface for tracing enforcement tests
Executor = BatchExecutor


async def execute(executor: BatchExecutor, limit: int | None, query: str | None = None) -> None:
    """Execute the pipeline with the given executor.

    Convenience function for executing a pipeline with tracing.

    Args:
        executor: The BatchExecutor instance to use.
        limit: Maximum number of records to process.
        query: Optional query string for data source filtering.

    """
    await executor.execute(limit, query)


async def process(
    executor: BatchExecutor,
    records: list[dict],
    start_index: int = 0,
) -> BatchResult:
    """Process a batch of records through the ETL pipeline.

    Convenience function for processing a batch with tracing.

    Args:
        executor: The BatchExecutor instance to use.
        records: Raw records to process.
        start_index: Starting index for records in this batch.

    Returns:
        BatchResult with counts for each layer.

    """
    return await executor.process(records, start_index)
