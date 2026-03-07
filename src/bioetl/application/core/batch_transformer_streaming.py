"""Streaming batch processing helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.core.batch_transformer import (
        BatchTransformer,
        TransformResult,
    )
    from bioetl.domain.ports import MemoryMonitorPort
    from bioetl.domain.types import BatchID, BronzeRecord


class StreamingBatchProcessor:
    """Memory-efficient streaming processor for large batches."""

    def __init__(
        self,
        transformer: BatchTransformer,
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
        """Process records in memory-efficient sub-batches."""
        current_chunk_size = chunk_size
        i = 0
        total_records = len(records)

        while i < total_records:
            if self._memory_monitor:
                current_chunk_size = self._memory_monitor.get_recommended_batch_size(
                    current_chunk_size
                )

            chunk = records[i : i + current_chunk_size]
            result = await self._transformer.transform_stream(
                chunk, batch_id, start_index + i
            )

            yield result
            i += len(chunk)

    def iter_records(self, records: list[BronzeRecord]) -> Iterator[BronzeRecord]:
        """Iterate over records without loading all into memory."""
        yield from records


__all__ = ["StreamingBatchProcessor"]
