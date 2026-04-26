"""Bronze layer writer (local storage with JSONL + zstd compression)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

import orjson
import zstandard as zstd

from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.infrastructure.storage.bronze.io_mixin import BronzeWriterIOMixin
from bioetl.infrastructure.storage.bronze.metadata_mixin import (
    BronzeWriterMetadataMixin,
)
from bioetl.infrastructure.storage.bronze.metrics_mixin import (
    BronzeWriterMetricsMixin,
)
from bioetl.infrastructure.storage.bronze.pipeline_helpers import (
    BronzeWriteArtifacts,
    BronzeWritePostwriteContext,
    BronzeWritePrepared,
    BronzeWriteRequest,
    build_bronze_write_artifacts,
    prepare_bronze_write,
)
from bioetl.infrastructure.storage.bronze.side_effects_mixin import (
    BronzeWriterSideEffectsMixin,
)
from bioetl.infrastructure.storage.bronze.validation_mixin import (
    BronzeWriterValidationMixin,
)
from bioetl.infrastructure.storage.support.atomic_ops import atomic_write_bytes

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.ports import (
        AuditPort,
        LineageStorePort,
        LoggerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        MetricsPort,
        TracingPort,
    )
from bioetl.domain.ports.noop import _NoOpSpan

__all__ = ["BRONZE_WRITE_ERRORS", "BronzeWriter"]

BRONZE_WRITE_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    zstd.ZstdError,
)
BRONZE_REQUIRED_METADATA_FIELDS = (
    "ingestion_ts",
    "run_id",
    "run_type",
    "batch_id",
)


@dataclass(frozen=True, slots=True)
class BronzeWriterRuntimeServices:
    """Optional Bronze runtime collaborators grouped behind one local seam."""

    tracing: TracingPort | None
    audit: AuditPort | None
    metadata_writer: MetadataWriterPort
    save_metadata: bool
    metadata_coordinator: MetadataCoordinatorPort | None
    lineage_store: LineageStorePort | None = None


class BronzeWriter(
    BronzeWriterValidationMixin,
    BronzeWriterMetadataMixin,
    BronzeWriterSideEffectsMixin,
    BronzeWriterIOMixin,
    BronzeWriterMetricsMixin,
):
    """Writer for Bronze layer (raw data in JSONL + zstd)."""

    COMPRESSION_CHUNK_SIZE = 256 * 1024
    COMPRESSION_LEVEL = 3
    COMPRESSION_THREADS = -1
    BRONZE_PATH_FORMAT = "{provider}/{entity}/{date}/{filename}"
    BRONZE_FILE_SUFFIX = ".jsonl.zst"
    # Keep required Bronze lineage metadata keys explicit in this facade module
    # for architecture invariant checks and maintainability.
    BRONZE_REQUIRED_METADATA_FIELDS: tuple[str, ...] = (
        "ingestion_ts",
        "run_id",
        "run_type",
        "batch_id",
    )
    BRONZE_METADATA_SIDECAR_SUFFIX = ".meta.json"

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        metrics: MetricsPort,
        save_json: bool = False,
        json_path: str | None = None,
        validate_json: bool = True,
        runtime_services: BronzeWriterRuntimeServices | None = None,
        flat_structure: bool = False,
        **legacy_kwargs: object,
    ) -> None:
        """Initialize Bronze writer."""
        tracing = cast("TracingPort | None", legacy_kwargs.pop("tracing", None))
        audit = cast("AuditPort | None", legacy_kwargs.pop("audit", None))
        metadata_writer = cast(
            "MetadataWriterPort | None",
            legacy_kwargs.pop("metadata_writer", None),
        )
        save_metadata = legacy_kwargs.pop("save_metadata", False)
        metadata_coordinator = cast(
            "MetadataCoordinatorPort | None",
            legacy_kwargs.pop("metadata_coordinator", None),
        )
        lineage_store = cast(
            "LineageStorePort | None",
            legacy_kwargs.pop("lineage_store", None),
        )
        if legacy_kwargs:
            unexpected = ", ".join(sorted(legacy_kwargs))
            raise TypeError(f"Unexpected BronzeWriter options: {unexpected}")

        if metadata_writer is None:
            from bioetl.domain.ports.noop import NoOpMetadataWriter

            metadata_writer = NoOpMetadataWriter()
        services = runtime_services or BronzeWriterRuntimeServices(
            tracing=tracing,
            audit=audit,
            metadata_writer=metadata_writer,
            save_metadata=bool(save_metadata),
            metadata_coordinator=metadata_coordinator,
            lineage_store=lineage_store,
        )

        self.base_path = Path(base_path)
        self.logger = logger
        self._logger: LoggerPort = logger
        self._metrics = metrics
        self.save_json = save_json
        self.json_path = json_path or str(self.base_path / "json")
        self.validate_json = validate_json
        self._audit = services.audit
        self._tracing = services.tracing
        self._metadata_writer = services.metadata_writer
        self._save_metadata = services.save_metadata
        self._metadata_coordinator = services.metadata_coordinator
        self._lineage_store = services.lineage_store
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
            BronzeWriteRequest(
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
        )

    async def _write_bronze_with_tracing(
        self,
        request: BronzeWriteRequest,
    ) -> BronzeWriteResult:
        span_context = (
            self._tracing.get_tracer(__name__).start_as_current_span("write_bronze")
            if self._tracing is not None
            else _NoOpSpan()
        )
        with span_context as span:
            span.set_attribute("provider", request.provider)
            span.set_attribute("entity", request.entity)
            span.set_attribute("batch_id", str(request.batch_id))
            span.set_attribute("run_id", str(request.run_id))

            labels = {"provider": request.provider, "entity": request.entity}
            self._metrics.increment_counter(
                "bioetl_bronze_write_attempts_total", 1, labels
            )
            start_time = time.perf_counter()
            prepared = self._prepare_bronze_write(request)
            write_artifacts = await self._write_bronze_data_and_sidecar(prepared)
            duration = time.perf_counter() - start_time
            await self._run_bronze_post_write_actions(
                BronzeWritePostwriteContext(
                    request=request,
                    prepared=prepared,
                    write_artifacts=write_artifacts,
                    duration=duration,
                )
            )
            total_duration = time.perf_counter() - start_time
            self._metrics.observe_histogram(
                "bioetl_bronze_write_total_duration_seconds",
                total_duration,
                labels,
            )
            return await self._build_bronze_write_result(
                prepared=prepared,
                batch_id=request.batch_id,
                record_count=write_artifacts.record_count,
                uncompressed_size=write_artifacts.uncompressed_size,
                compressed_size=write_artifacts.compressed_size,
                span=span,
            )

    def _validate_bronze_request_inputs(self, request: BronzeWriteRequest) -> None:
        """Keep Bronze request validation explicit in the writer facade."""
        self._validate_bronze_names(request.provider, request.entity)
        self._validate_records_iterator(request.records)
        self._validate_utc_datetime(request.date, "date")
        self._validate_utc_datetime(request.ingestion_ts, "ingestion_ts")

    def _build_bronze_metadata(
        self,
        run_id: RunID,
        run_type: RunType,
        effective_ts: datetime,
        provider: str,
        entity: str,
        batch_id: BatchID,
    ) -> dict[str, str]:
        """Expose Bronze metadata construction on the writer facade."""
        return BronzeWriterMetadataMixin._build_bronze_metadata(
            self,
            run_id=run_id,
            run_type=run_type,
            effective_ts=effective_ts,
            provider=provider,
            entity=entity,
            batch_id=batch_id,
        )

    def _prepare_bronze_write(
        self,
        request: BronzeWriteRequest,
    ) -> BronzeWritePrepared:
        """Validate inputs and build the prepared write context."""
        return prepare_bronze_write(self, request)

    async def _run_bronze_post_write_actions(
        self,
        context: BronzeWritePostwriteContext,
    ) -> None:
        """Emit metrics, optional JSON copy, audit log, and metadata sidecar."""
        request = context.request
        prepared = context.prepared
        write_artifacts = context.write_artifacts
        self._emit_bronze_write_metrics(
            duration=context.duration,
            provider=request.provider,
            entity=request.entity,
            record_count=write_artifacts.record_count,
            compressed_size=write_artifacts.compressed_size,
            uncompressed_size=write_artifacts.uncompressed_size,
            relative_path=prepared.relative_path,
            batch_id=request.batch_id,
            run_id=request.run_id,
            run_type=request.run_type,
        )
        if self.save_json:
            await self._write_json_copy(
                prepared.record_list,
                request.provider,
                request.entity,
                prepared.date_str,
                request.batch_id,
            )
        if self._audit:
            await self._log_bronze_audit(
                run_id=request.run_id,
                ingestion_ts=request.ingestion_ts,
                relative_path=prepared.relative_path,
                batch_id=request.batch_id,
                run_type=request.run_type,
                record_count=write_artifacts.record_count,
                compressed_size=write_artifacts.compressed_size,
                uncompressed_size=write_artifacts.uncompressed_size,
                provider=request.provider,
                entity=request.entity,
            )
        if self._save_metadata:
            await self._maybe_write_bronze_metadata(
                run_id=request.run_id,
                run_type=request.run_type,
                provider=request.provider,
                entity=request.entity,
                batch_id=request.batch_id,
                record_count=write_artifacts.record_count,
                compressed_size=write_artifacts.compressed_size,
                relative_path=prepared.relative_path,
                ingestion_ts=request.ingestion_ts,
                duration=context.duration,
                source_metadata=request.source_metadata,
            )

    async def _write_bronze_data_and_sidecar(
        self,
        prepared: BronzeWritePrepared,
    ) -> BronzeWriteArtifacts:
        """Write compressed JSONL data and metadata sidecar to disk."""

        def _write_task() -> tuple[int, int]:
            count, size = self._write_atomic_stream(
                prepared.records_iter,
                prepared.full_path,
            )
            meta_bytes = orjson.dumps(prepared.metadata, option=orjson.OPT_SORT_KEYS)
            atomic_write_bytes(prepared.meta_path, meta_bytes)
            return count, size

        record_count, uncompressed_size = await asyncio.to_thread(_write_task)
        return build_bronze_write_artifacts(
            full_path=prepared.full_path,
            record_count=record_count,
            uncompressed_size=uncompressed_size,
        )
