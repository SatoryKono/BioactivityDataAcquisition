"""Streaming batch processing helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.application.core.transformer_runtime.state import TransformResult
    from bioetl.domain.ports import MemoryMonitorPort
    from bioetl.domain.types import BatchID, BronzeRecord


class _StreamingTransformer(Protocol):
    """Structural transform contract required by the streaming helper."""

    async def transform_stream(
        self,
        records: list[BronzeRecord],
        batch_id: BatchID,
        start_index: int = 0,
    ) -> TransformResult: ...


class StreamingBatchProcessor:
    """Memory-efficient streaming processor for large batches."""

    def __init__(
        self,
        transformer: _StreamingTransformer,
        memory_monitor: MemoryMonitorPort | None = None,
    ) -> None:
        """Initialize streaming processor."""
        self._transformer = transformer
        self._memory_monitor = memory_monitor

    async def process_in_chunks(
        self,
        records: list[BronzeRecord],
        batch_id: BatchID,
        chunk_size: int = 100,
        start_index: int = 0,
    ) -> AsyncIterator[TransformResult]:
        """Process records in memory-efficient sub-batches.
        Args:
            records: Full list of Bronze records to process in chunks.
            batch_id: Batch identifier shared across all chunks.
            chunk_size: Initial maximum number of records per sub-batch.
            start_index: Absolute record index of the first record for accurate reporting.
        """
        if chunk_size < 1:
            raise ValueError(f"chunk_size must be >= 1, got {chunk_size!r}")
        current_chunk_size = chunk_size
        i = 0
        total_records = len(records)
        while i < total_records:
            if self._memory_monitor:
                current_chunk_size = self._memory_monitor.get_recommended_batch_size(
                    current_chunk_size
                )
            if current_chunk_size < 1:
                current_chunk_size = 1
            batch_slice = records[i : i + current_chunk_size]
            result = await self._transformer.transform_stream(
                batch_slice, batch_id, start_index + i
            )
            yield result
            i += len(batch_slice)

    def iter_records(self, records: list[BronzeRecord]) -> Iterator[BronzeRecord]:
        """Iterate over records without loading all into memory.
        Args:
            records: List of Bronze records to iterate.
        Returns:
            Iterator yielding each record in order.
        """
        yield from records


__all__ = ["StreamingBatchProcessor"]
