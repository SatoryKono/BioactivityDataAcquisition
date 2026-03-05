"""Bronze layer writer (local storage with JSONL + zstd compression)."""

from __future__ import annotations

__all__ = ["BRONZE_WRITE_ERRORS", "BronzeWriter"]


import asyncio
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import orjson
import zstandard as zstd

from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.types import BatchID, JsonDict, RunID, RunType
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
    from bioetl.domain.models.metadata import BronzeMetadata, SourceMetadata
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


@dataclass(frozen=True, slots=True)
class _BronzeWritePrepared:
    records_iter: Iterator[bytes]
    record_list: list[bytes]
    date_str: str
    relative_path: str
    metadata: JsonDict  # Any: lightweight write-side metadata sidecar payload
    full_path: Path
    meta_path: Path


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
        return await self._write_bronze_with_tracing(
            records=records,
            provider=provider,
            entity=entity,
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
            source_metadata=source_metadata,
        )

    async def _write_bronze_with_tracing(
        self,
        *,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
        source_metadata: SourceMetadata | None,
    ) -> BronzeWriteResult:
        tracer = self._tracing.get_tracer(__name__)
        with tracer.start_as_current_span("write_bronze") as span:
            span.set_attribute("provider", provider)
            span.set_attribute("entity", entity)
            span.set_attribute("batch_id", str(batch_id))
            span.set_attribute("run_id", str(run_id))

            start_time = time.perf_counter()
            prepared = self._prepare_bronze_write(
                records=records,
                provider=provider,
                entity=entity,
                date=date,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
                ingestion_ts=ingestion_ts,
            )
            (
                record_count,
                uncompressed_size,
                compressed_size,
            ) = await self._write_bronze_data_and_sidecar(prepared)
            duration = time.perf_counter() - start_time
            await self._run_bronze_post_write_actions(
                prepared=prepared,
                provider=provider,
                entity=entity,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
                ingestion_ts=ingestion_ts,
                record_count=record_count,
                uncompressed_size=uncompressed_size,
                compressed_size=compressed_size,
                duration=duration,
                source_metadata=source_metadata,
            )
            return await self._build_bronze_write_result(
                prepared=prepared,
                batch_id=batch_id,
                record_count=record_count,
                uncompressed_size=uncompressed_size,
                compressed_size=compressed_size,
                span=span,
            )

    def _prepare_bronze_write(
        self,
        *,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> _BronzeWritePrepared:
        self._validate_bronze_names(provider, entity)
        self._validate_records_iterator(records)
        self._validate_utc_datetime(date, "date")
        self._validate_utc_datetime(ingestion_ts, "ingestion_ts")

        validated_records = iter(records)
        if self.validate_json:
            validated_records = self._validate_json_records(validated_records)

        date_str = date.strftime("%Y-%m-%d")
        filename = f"batch_{date_str}_{batch_id}.jsonl.zst"
        relative_path = self._resolve_bronze_path(provider, entity, date_str, filename)
        metadata = self._build_bronze_metadata(
            run_id, run_type, ingestion_ts, provider, entity, batch_id
        )
        if self.save_json:
            record_list = list(validated_records)
            records_iter = iter(record_list)
        else:
            record_list = cast(list[bytes], [])
            records_iter = validated_records

        full_path = self.base_path / relative_path
        meta_path = full_path.with_suffix(".zst.meta.json")
        return _BronzeWritePrepared(
            records_iter=records_iter,
            record_list=record_list,
            date_str=date_str,
            relative_path=relative_path,
            metadata=metadata,
            full_path=full_path,
            meta_path=meta_path,
        )

    async def _write_bronze_data_and_sidecar(
        self,
        prepared: _BronzeWritePrepared,
    ) -> tuple[int, int, int]:
        loop = asyncio.get_running_loop()

        def _write_task() -> tuple[int, int]:
            count, size = self._write_atomic_stream(
                prepared.records_iter,
                prepared.full_path,
            )
            meta_bytes = orjson.dumps(prepared.metadata, option=orjson.OPT_SORT_KEYS)
            atomic_write_bytes(prepared.meta_path, meta_bytes)
            return count, size

        record_count, uncompressed_size = await loop.run_in_executor(None, _write_task)
        compressed_size = prepared.full_path.stat().st_size
        return record_count, uncompressed_size, compressed_size

    async def _run_bronze_post_write_actions(
        self,
        *,
        prepared: _BronzeWritePrepared,
        provider: str,
        entity: str,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
        record_count: int,
        uncompressed_size: int,
        compressed_size: int,
        duration: float,
        source_metadata: SourceMetadata | None,
    ) -> None:
        self._emit_bronze_write_metrics(
            duration=duration,
            provider=provider,
            entity=entity,
            record_count=record_count,
            compressed_size=compressed_size,
            uncompressed_size=uncompressed_size,
            relative_path=prepared.relative_path,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
        )
        if self.save_json:
            await self._write_json_copy(
                prepared.record_list,
                provider,
                entity,
                prepared.date_str,
                batch_id,
            )
        if self._audit:
            await self._log_bronze_audit(
                run_id=run_id,
                ingestion_ts=ingestion_ts,
                relative_path=prepared.relative_path,
                batch_id=batch_id,
                run_type=run_type,
                record_count=record_count,
                compressed_size=compressed_size,
                uncompressed_size=uncompressed_size,
                provider=provider,
                entity=entity,
            )
        if self._save_metadata:
            await self._maybe_write_bronze_metadata(
                run_id=run_id,
                run_type=run_type,
                provider=provider,
                entity=entity,
                batch_id=batch_id,
                record_count=record_count,
                compressed_size=compressed_size,
                relative_path=prepared.relative_path,
                ingestion_ts=ingestion_ts,
                duration=duration,
                source_metadata=source_metadata,
            )

    async def _log_bronze_audit(
        self,
        *,
        run_id: RunID,
        ingestion_ts: datetime,
        relative_path: str,
        batch_id: BatchID,
        run_type: RunType,
        record_count: int,
        compressed_size: int,
        uncompressed_size: int,
        provider: str,
        entity: str,
    ) -> None:
        if not self._audit:
            return
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

    async def _build_bronze_write_result(
        self,
        *,
        prepared: _BronzeWritePrepared,
        batch_id: BatchID,
        record_count: int,
        uncompressed_size: int,
        compressed_size: int,
        span: Any,  # Any: OpenTelemetry span interface is runtime-dependent
    ) -> BronzeWriteResult:
        span.set_attribute("record_count", record_count)
        span.set_attribute("compressed_size", compressed_size)
        checksum = await self._calculate_checksum(prepared.full_path)
        return BronzeWriteResult(
            batch_id=batch_id,
            relative_path=prepared.relative_path,
            absolute_path=str(prepared.full_path),
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
        bronze_metadata = self._create_bronze_metadata_payload(
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
        metadata_base_path = self._resolve_bronze_metadata_base_path(provider, entity)
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

    def _create_bronze_metadata_payload(
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
    ) -> BronzeMetadata:
        """Build bronze metadata via coordinator when configured, else fallback."""
        completed_at = ingestion_ts + timedelta(seconds=duration)
        if self._metadata_coordinator is None:
            return self._build_full_bronze_metadata(
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

        from bioetl.domain.ports import BronzeMetadataInput

        bronze_input = BronzeMetadataInput(
            batch_id=batch_id,
            record_count=record_count,
            compressed_size=compressed_size,
            output_path=relative_path,
            started_at=ingestion_ts,
            completed_at=completed_at,
            source_metadata=source_metadata,
            query_string=source_metadata.query_string if source_metadata else None,
        )
        return self._metadata_coordinator.create_bronze_metadata(bronze_input)

    def _resolve_bronze_metadata_base_path(self, provider: str, entity: str) -> Path:
        """Resolve base path for bronze metadata sidecar output."""
        if self._flat_structure:
            return self.base_path
        return self.base_path / provider / entity
