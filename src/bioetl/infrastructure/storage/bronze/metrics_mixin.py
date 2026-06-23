"""Metrics/logging helper mixin for BronzeWriter."""

from __future__ import annotations

from typing import Protocol

from bioetl.domain.ports import LoggerPort, MetricsPort
from bioetl.domain.types import BatchID, RunID, RunType


class _BronzeWriterMetricsHost(Protocol):
    """Structural host contract for metrics/logging capabilities."""

    _metrics: MetricsPort
    logger: LoggerPort


class BronzeWriterMetricsMixin:
    """Shared metrics emission for Bronze writer workflows."""

    def _emit_bronze_write_metrics(
        self: _BronzeWriterMetricsHost,
        *,
        duration: float,
        provider: str,
        entity: str,
        record_count: int,
        compressed_size: int,
        uncompressed_size: int,
        relative_path: str,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Emit metrics counters and structured log for a bronze write.

        Args:
            duration: Total write duration in seconds.
            provider: Data provider name used as metric label.
            entity: Entity type name used as metric label.
            record_count: Number of records written.
            compressed_size: Compressed byte size of the written file.
            uncompressed_size: Uncompressed byte size of all records.
            relative_path: Relative path of the written file for logging.
            batch_id: Unique batch identifier for the log entry.
            run_id: Pipeline run identifier for the log entry.
            run_type: Run classification for the log entry.
        """
        labels = {"provider": provider, "entity": entity}

        self._metrics.observe_histogram(
            "bioetl_bronze_write_duration_seconds",
            duration,
            labels,
        )
        self._metrics.increment_counter(
            "bioetl_bronze_records_written_total",
            record_count,
            labels,
        )
        self._metrics.increment_counter(
            "bioetl_bronze_bytes_written_total",
            compressed_size,
            labels,
        )

        self.logger.info(
            "bronze_write_complete",
            path=relative_path,
            provider=provider,
            entity=entity,
            batch_id=str(batch_id),
            run_id=str(run_id),
            run_type=run_type.value,
            record_count=record_count,
            compressed_bytes=compressed_size,
            uncompressed_bytes=uncompressed_size,
            duration_seconds=round(duration, 3),
        )


__all__ = ["BronzeWriterMetricsMixin"]
