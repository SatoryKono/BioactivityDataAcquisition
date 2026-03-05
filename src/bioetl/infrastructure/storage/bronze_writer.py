"""Bronze layer writer (local storage with JSONL + zstd compression)."""

from __future__ import annotations

__all__ = ["BRONZE_WRITE_ERRORS", "BronzeWriter"]


import asyncio
import time
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, cast

import orjson
import zstandard as zstd

from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.infrastructure.storage._atomic import atomic_write_bytes
from bioetl.infrastructure.storage.bronze_writer_io_mixin import BronzeWriterIOMixin
from bioetl.infrastructure.storage.bronze_writer_metadata_mixin import (
    BronzeWriterMetadataMixin,
)
from bioetl.infrastructure.storage.bronze_writer_validation_mixin import (
    BronzeWriterValidationMixin,
)

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        MetricsPort,
        TracingPort,
    )

BRONZE_WRITE_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    zstd.ZstdError,
)


class BronzeWriter(
    BronzeWriterValidationMixin,
    BronzeWriterMetadataMixin,
    BronzeWriterIOMixin,
):
    """Writer for Bronze layer (raw data in JSONL + zstd)."""

    COMPRESSION_CHUNK_SIZE = 256 * 1024
    COMPRESSION_LEVEL = 3
    COMPRESSION_THREADS = -1
    BRONZE_PATH_FORMAT = "{provider}/{entity}/{date}/{filename}"
    BRONZE_FILE_SUFFIX = ".jsonl.zst"

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        metrics: MetricsPort,
        tracing: TracingPort | None = None,
        save_json: bool = False,
        json_path: str | None = None,
        validate_json: bool = True,
        audit: AuditPort | None = None,
        metadata_writer: MetadataWriterPort | None = None,
        save_metadata: bool = False,
        metadata_coordinator: MetadataCoordinatorPort | None = None,
        flat_structure: bool = False,
    ) -> None:
        """Initialize Bronze writer."""
        if tracing is None:
            from bioetl.domain.ports import NoOpTracing

            tracing = NoOpTracing()

        if metadata_writer is None:
            from bioetl.domain.ports import NoOpMetadataWriter

            metadata_writer = NoOpMetadataWriter()

        self.base_path = Path(base_path)
        self.logger = logger
        self._metrics = metrics
        self.save_json = save_json
        self.json_path = json_path or str(self.base_path / "json")
        self.validate_json = validate_json
        self._audit = audit
        self._tracing: TracingPort = tracing
        self._metadata_writer: MetadataWriterPort = metadata_writer
        self._save_metadata = save_metadata
        self._metadata_coordinator: MetadataCoordinatorPort | None = (
            metadata_coordinator
        )
        self._flat_structure = flat_structure

    async def write_bronze(
        self,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
        source_metadata: SourceMetadata | None = None,
    ) -> BronzeWriteResult:
        """Write raw records to Bronze layer (JSONL + zstd)."""
        tracer = self._tracing.get_tracer(__name__)
        with tracer.start_as_current_span("write_bronze") as span:
            span.set_attribute("provider", provider)
            span.set_attribute("entity", entity)
            span.set_attribute("batch_id", str(batch_id))
            span.set_attribute("run_id", str(run_id))

            start_time = time.perf_counter()

            self._validate_bronze_names(provider, entity)
            self._validate_records_iterator(records)
            self._validate_utc_datetime(date, "date")
            self._validate_utc_datetime(ingestion_ts, "ingestion_ts")

            records = iter(records)
            if self.validate_json:
                records = self._validate_json_records(records)

            date_str = date.strftime("%Y-%m-%d")
            filename = f"batch_{date_str}_{batch_id}.jsonl.zst"
            relative_path = self._resolve_bronze_path(
                provider, entity, date_str, filename
            )
            metadata = self._build_bronze_metadata(
                run_id, run_type, ingestion_ts, provider, entity, batch_id
            )

            loop = asyncio.get_running_loop()

            if self.save_json:
                record_list = list(records)
                records_iter = iter(record_list)
            else:
                record_list = cast(list[bytes], [])
                records_iter = records

            full_path = self.base_path / relative_path
            meta_path = full_path.with_suffix(".zst.meta.json")

            def _write_task() -> tuple[int, int]:
                count, size = self._write_atomic_stream(records_iter, full_path)
                meta_bytes = orjson.dumps(metadata, option=orjson.OPT_SORT_KEYS)
                atomic_write_bytes(meta_path, meta_bytes)
                return count, size

            record_count, uncompressed_size = await loop.run_in_executor(
                None, _write_task
            )
            compressed_size = full_path.stat().st_size

            duration = time.perf_counter() - start_time

            self._emit_bronze_write_metrics(
                duration=duration,
                provider=provider,
                entity=entity,
                record_count=record_count,
                compressed_size=compressed_size,
                uncompressed_size=uncompressed_size,
                relative_path=relative_path,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
            )

            if self.save_json:
                await self._write_json_copy(
                    record_list, provider, entity, date_str, batch_id
                )

            if self._audit:
                audit_entry = AuditEntry(
                    run_id=run_id,
                    timestamp=ingestion_ts,
                    layer=AuditLayer.BRONZE,
                    table_name=relative_path,
                    operation=AuditOperation.WRITE,
                    records_count=record_count,
                    metadata={
                        "provider": provider,
                        "entity": entity,
                        "batch_id": str(batch_id),
                        "run_type": run_type.value,
                        "compressed_bytes": compressed_size,
                        "uncompressed_bytes": uncompressed_size,
                    },
                )
                await self._audit.log_write(audit_entry)

            if self._save_metadata:
                await self._maybe_write_bronze_metadata(
                    run_id=run_id,
                    run_type=run_type,
                    provider=provider,
                    entity=entity,
                    batch_id=batch_id,
                    record_count=record_count,
                    compressed_size=compressed_size,
                    relative_path=relative_path,
                    ingestion_ts=ingestion_ts,
                    duration=duration,
                    source_metadata=source_metadata,
                )

            span.set_attribute("record_count", record_count)
            span.set_attribute("compressed_size", compressed_size)

            checksum = await self._calculate_checksum(full_path)

            return BronzeWriteResult(
                batch_id=batch_id,
                relative_path=relative_path,
                absolute_path=str(full_path),
                record_count=record_count,
                compressed_size=compressed_size,
                uncompressed_size=uncompressed_size,
                checksum_blake2=checksum,
            )

    def _emit_bronze_write_metrics(
        self,
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
        """Emit metrics counters and structured log for a bronze write."""
        labels = {"provider": provider, "entity": entity}

        self._metrics.observe_histogram(
            "bronze_write_duration_seconds",
            duration,
            labels,
        )
        self._metrics.increment_counter(
            "bronze_records_written_total",
            record_count,
            labels,
        )
        self._metrics.increment_counter(
            "bronze_bytes_written_total",
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

    async def _maybe_write_bronze_metadata(
        self,
        *,
        run_id: RunID,
        run_type: RunType,
        provider: str,
        entity: str,
        batch_id: BatchID,
        record_count: int,
        compressed_size: int,
        relative_path: str,
        ingestion_ts: datetime,
        duration: float,
        source_metadata: SourceMetadata | None,
    ) -> None:
        """Create and persist bronze metadata via coordinator or fallback."""
        completed_at = ingestion_ts + timedelta(seconds=duration)

        if self._metadata_coordinator is not None:
            from bioetl.domain.ports import BronzeMetadataInput

            query_string = source_metadata.query_string if source_metadata else None
            bronze_input = BronzeMetadataInput(
                batch_id=batch_id,
                record_count=record_count,
                compressed_size=compressed_size,
                output_path=relative_path,
                started_at=ingestion_ts,
                completed_at=completed_at,
                source_metadata=source_metadata,
                query_string=query_string,
            )
            bronze_metadata = self._metadata_coordinator.create_bronze_metadata(
                bronze_input
            )
        else:
            bronze_metadata = self._build_full_bronze_metadata(
                run_id=run_id,
                run_type=run_type,
                provider=provider,
                entity=entity,
                batch_id=batch_id,
                record_count=record_count,
                compressed_size=compressed_size,
                output_path=relative_path,
                started_at=ingestion_ts,
                completed_at=completed_at,
                duration_seconds=duration,
                source_metadata=source_metadata,
            )

        if self._flat_structure:
            metadata_base_path = self.base_path
        else:
            metadata_base_path = self.base_path / provider / entity
        await self._metadata_writer.write_bronze_metadata(
            base_path=metadata_base_path,
            metadata=bronze_metadata,
            provider=provider,
            entity=entity,
        )
        self.logger.debug(
            "bronze_metadata_written",
            metadata_path=str(
                metadata_base_path / f"{provider}_{entity}_metadata.yaml"
            ),
            run_id=str(run_id),
        )
