"""Metadata and audit helpers for SilverWriter."""

from __future__ import annotations

__all__ = ["SilverWriterMetadataMixin"]

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import ClassVar, Protocol

import pyarrow as pa
from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.ports import (
    AuditEntry,
    AuditLayer,
    AuditOperation,
    AuditPort,
    LoggerPort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    SilverMetadataInput,
)
from bioetl.domain.services.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.metadata_builder import _parse_table_name


@dataclass(frozen=True, slots=True)
class _SilverMetadataWriteRequest:
    """Normalized request payload for one standard Silver metadata write."""

    table_path: str
    table_name: str
    records: list[BronzeRecord]
    primary_keys: list[str]
    mode: SilverWriteMode
    bronze_refs: list[BronzeWriteResult] | None = None
    dq_metrics: BatchDQMetrics | None = None
    dq_report_path: str | None = None
    partition_by: list[str] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    version_after: int | None = None


@dataclass(frozen=True, slots=True)
class _SilverMergedMetadataWriteRequest:
    """Normalized request payload for one merged Silver metadata write."""

    table_path: str
    table_name: str
    records: list[BronzeRecord]
    primary_keys: list[str]
    run_id: str | None = None
    sources_used: list[str] | None = None


@dataclass(frozen=True, slots=True)
class _PreparedSilverMetadataWriteOperation:
    """Prepared Silver metadata operation carried into sidecar execution."""

    request: _SilverMetadataWriteRequest | _SilverMergedMetadataWriteRequest
    provider_name: str
    entity_name: str
    metadata: SilverMetadata


@dataclass(frozen=True, slots=True)
class _ResolvedSilverMetadataContext:
    """Shared provider/entity/version context for Silver metadata preparation."""

    provider_name: str
    entity_name: str
    version_after: int | None


@dataclass(frozen=True, slots=True)
class _PreparedSilverWriteFinalizationContext:
    """Prepared metadata/result context for one completed Silver write."""

    dq_metrics: BatchDQMetrics
    version_after: int | None
    completed_at: datetime


def _build_silver_write_result(
    *, table_name: str, table_path: str, version_after: int | None, records_count: int
) -> SilverWriteResult | None:
    return None if version_after is None else SilverWriteResult(
        table_name, table_path, version_after, records_count
    )


class _SilverMetadataWriteHostProtocol(Protocol):
    """Typed host contract for Silver metadata sidecar stages."""

    logger: LoggerPort
    _metadata_coordinator: MetadataCoordinatorPort | None
    _metadata_writer: MetadataWriterPort
    _flat_structure: bool
    _transform_version: str | None
    _transform_steps: tuple[str, ...]

    async def _get_delta_version(self, table_path: str) -> int | None: ...

    async def _write_silver_metadata_file(
        self,
        *,
        table_path: str,
        metadata: SilverMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None: ...


def _read_delta_version(table_path: str) -> int:
    """Read the current Delta table version synchronously."""
    return DeltaTable(table_path).version()


async def _resolve_silver_metadata_context(
    host: _SilverMetadataWriteHostProtocol,
    *,
    table_path: str,
    table_name: str,
    version_after: int | None = None,
) -> _ResolvedSilverMetadataContext:
    """Resolve shared provider/entity/version context for Silver metadata writes."""
    provider_name, entity_name = _parse_table_name(table_name)
    version = version_after if version_after is not None else await host._get_delta_version(table_path)
    return _ResolvedSilverMetadataContext(provider_name, entity_name, version)


async def _prepare_silver_metadata_write(
    host: _SilverMetadataWriteHostProtocol,
    request: _SilverMetadataWriteRequest,
) -> _PreparedSilverMetadataWriteOperation:
    """Resolve provider/entity and build standard Silver metadata payload."""
    context = await _resolve_silver_metadata_context(
        host,
        table_path=request.table_path,
        table_name=request.table_name,
        version_after=request.version_after,
    )
    assert host._metadata_coordinator is not None
    silver_input = SilverMetadataInput(
        table_path=request.table_path,
        records=request.records,
        primary_keys=request.primary_keys,
        mode=request.mode,
        bronze_refs=request.bronze_refs,
        dq_metrics=request.dq_metrics,
        version_after=context.version_after,
        transform_version=host._transform_version,
        transform_steps=host._transform_steps,
        dq_report_path=request.dq_report_path,
        partition_by=request.partition_by,
        started_at=request.started_at,
        completed_at=request.completed_at,
    )
    metadata = host._metadata_coordinator.create_silver_metadata(silver_input)
    return _PreparedSilverMetadataWriteOperation(request, context.provider_name, context.entity_name, metadata)


async def _prepare_silver_merged_metadata_write(
    host: _SilverMetadataWriteHostProtocol,
    request: _SilverMergedMetadataWriteRequest,
) -> _PreparedSilverMetadataWriteOperation:
    """Resolve provider/entity and build merged Silver metadata payload."""
    from bioetl.infrastructure.storage.metadata_builder import SilverMetadataBuilder

    context = await _resolve_silver_metadata_context(
        host,
        table_path=request.table_path,
        table_name=request.table_name,
    )
    builder = SilverMetadataBuilder(
        transform_version=host._transform_version, transform_steps=host._transform_steps
    )
    metadata = builder.build_merged_metadata(
        table_path=request.table_path,
        table_name=request.table_name,
        records=request.records,
        primary_keys=request.primary_keys,
        run_id=request.run_id,
        sources_used=request.sources_used,
        version_after=context.version_after,
    )
    return _PreparedSilverMetadataWriteOperation(request, context.provider_name, context.entity_name, metadata)


async def _execute_prepared_silver_metadata_write_operation(
    host: _SilverMetadataWriteHostProtocol,
    prepared: _PreparedSilverMetadataWriteOperation,
) -> None:
    """Execute one prepared Silver metadata operation via the canonical writer handoff."""
    await host._write_silver_metadata_file(
        table_path=prepared.request.table_path,
        metadata=prepared.metadata,
        table_name=prepared.request.table_name,
        provider_name=prepared.provider_name,
        entity_name=prepared.entity_name,
    )


async def _execute_silver_metadata_write(
    host: _SilverMetadataWriteHostProtocol,
    request: _SilverMetadataWriteRequest | _SilverMergedMetadataWriteRequest,
    prepare: Callable[..., Awaitable[_PreparedSilverMetadataWriteOperation]],
) -> None:
    """Prepare and persist one Silver metadata write via the canonical lifecycle."""
    prepared = await prepare(host, request)
    await _execute_prepared_silver_metadata_write_operation(host, prepared)


class SilverWriterMetadataMixin:
    """Mixin with metadata, lineage, and audit helpers."""

    logger: LoggerPort
    _audit: AuditPort | None
    _metadata_coordinator: MetadataCoordinatorPort | None
    _metadata_writer: MetadataWriterPort
    _flat_structure: bool
    _transform_version: str | None
    _transform_steps: tuple[str, ...]
    _dq_calculator: DQMetricsCalculator
    _get_table_schema: Callable[[str], Awaitable[pa.Schema | None]]
    _SILVER_AUDIT_OPERATION_MAP: ClassVar[dict[SilverWriteMode, AuditOperation]] = {
        SilverWriteMode.MERGE: AuditOperation.MERGE,
        SilverWriteMode.APPEND: AuditOperation.APPEND,
        SilverWriteMode.DELETE: AuditOperation.DELETE,
    }

    async def _compute_dq_metrics(
        self,
        table_name: str,
        records: list[BronzeRecord],
        quarantined_count: int = 0,
    ) -> BatchDQMetrics:
        """Compute DQ metrics using injected calculator."""
        from bioetl.domain.services.dq_metrics_calculator import DQMetricsInput

        existing_schema = await self._get_table_schema(table_name)
        existing_fields: set[str] | None = None
        if existing_schema is not None:
            existing_fields = set(existing_schema.names)

        input_data = DQMetricsInput(
            records=records,
            existing_schema_fields=existing_fields,
            quarantined_count=quarantined_count,
        )
        return self._dq_calculator.calculate(input_data)

    async def _log_silver_audit(
        self,
        table_name: str,
        records: list[BronzeRecord],
        mode: SilverWriteMode,
    ) -> None:
        """Log audit entry for Silver write operation."""
        if self._audit is None:
            return
        from uuid import UUID

        from bioetl.domain.types import RunID

        first_record = records[0]
        run_id_str = first_record.get("_run_id", "")
        ingestion_ts = first_record.get("_ingestion_ts")

        try:
            run_id = RunID(UUID(run_id_str))
        except (ValueError, TypeError):
            self.logger.warning(
                "audit_skipped_invalid_run_id",
                table=table_name,
                run_id=run_id_str,
            )
            return
        if isinstance(ingestion_ts, str):
            timestamp = datetime.fromisoformat(ingestion_ts)
        elif isinstance(ingestion_ts, datetime):
            timestamp = ingestion_ts
        else:
            timestamp = datetime.fromtimestamp(0, tz=UTC)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        operation = self._SILVER_AUDIT_OPERATION_MAP[mode]
        audit_entry = AuditEntry(
            run_id=run_id,
            timestamp=timestamp,
            layer=AuditLayer.SILVER,
            table_name=table_name,
            operation=operation,
            records_count=len(records),
            metadata={
                "run_type": first_record.get("_run_type", ""),
                "source_batch_id": first_record.get("_source_batch_id", ""),
            },
        )
        await self._audit.log_write(audit_entry)

    async def _get_delta_version(self, table_path: str) -> int | None:
        """Get current Delta table version, if table exists."""
        try:
            version = await asyncio.to_thread(_read_delta_version, table_path)
            return version
        except DeltaTableNotFoundError:
            return None

    def _should_skip_silver_metadata_write(
        self,
        *,
        records: list[BronzeRecord],
        table_path: str,
        event_name: str,
        use_debug_log: bool = False,
    ) -> bool:
        """Return whether Silver metadata write should short-circuit before prepare."""
        if not records:
            return True
        if self._metadata_coordinator is None:
            log = self.logger.debug if use_debug_log else self.logger.warning
            log(
                event_name,
                reason="MetadataCoordinator not configured",
                table_path=table_path,
            )
            return True
        return False

    async def _write_silver_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        mode: SilverWriteMode,
        bronze_refs: list[BronzeWriteResult] | None = None,
        dq_metrics: BatchDQMetrics | None = None,
        dq_report_path: str | None = None,
        partition_by: list[str] | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        version_after: int | None = None,
    ) -> None:
        """Write Silver layer metadata sidecar file."""
        if self._should_skip_silver_metadata_write(
            records=records,
            table_path=table_path,
            event_name="silver_metadata_skipped",
        ):
            return
        await _execute_silver_metadata_write(
            self,
            request=_SilverMetadataWriteRequest(
                table_path=table_path,
                table_name=table_name,
                records=records,
                primary_keys=primary_keys,
                mode=mode,
                bronze_refs=bronze_refs,
                dq_metrics=dq_metrics,
                dq_report_path=dq_report_path,
                partition_by=partition_by,
                started_at=started_at,
                completed_at=completed_at,
                version_after=version_after,
            ),
            prepare=_prepare_silver_metadata_write,
        )

    async def _write_silver_merged_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write Silver metadata sidecar for merged composite data."""
        if self._should_skip_silver_metadata_write(
            records=records,
            table_path=table_path,
            event_name="silver_merged_metadata_skipped",
            use_debug_log=True,
        ):
            return
        await _execute_silver_metadata_write(
            self,
            request=_SilverMergedMetadataWriteRequest(
                table_path=table_path,
                table_name=table_name,
                records=records,
                primary_keys=primary_keys,
                run_id=run_id,
                sources_used=sources_used,
            ),
            prepare=_prepare_silver_merged_metadata_write,
        )

    async def _write_silver_metadata_file(
        self,
        *,
        table_path: str,
        metadata: SilverMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None:
        """Persist one Silver metadata sidecar via the canonical writer handoff."""
        await self._metadata_writer.write_silver_metadata(
            table_path,
            metadata,
            table_name=table_name,
            flat_structure=self._flat_structure,
            provider=provider_name,
            entity=entity_name,
        )

    async def _maybe_log_silver_audit(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        mode: SilverWriteMode,
    ) -> None:
        """Guard for audit logging — only calls _log_silver_audit if enabled."""
        if self._audit and records:
            await self._log_silver_audit(table_name=table_name, records=records, mode=mode)

    async def _finalize_silver_write_result(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        table_path: str,
        primary_keys: list[str],
        validated_mode: SilverWriteMode,
        bronze_refs: list[BronzeWriteResult] | None,
        partition_cols: list[str] | None,
        started_at: datetime,
        start_perf: float,
    ) -> SilverWriteResult | None:
        """Compute DQ metrics, write metadata, and build final result."""
        context = await self._prepare_silver_write_finalization_context(
            table_name=table_name,
            records=records,
            table_path=table_path,
            started_at=started_at,
            start_perf=start_perf,
        )

        await self._write_silver_metadata(
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            mode=validated_mode,
            bronze_refs=bronze_refs,
            dq_metrics=context.dq_metrics,
            partition_by=partition_cols,
            started_at=started_at,
            completed_at=context.completed_at,
            version_after=context.version_after,
        )
        return _build_silver_write_result(
            table_name=table_name,
            table_path=table_path,
            version_after=context.version_after,
            records_count=len(records),
        )

    async def _prepare_silver_write_finalization_context(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        table_path: str,
        started_at: datetime,
        start_perf: float,
    ) -> _PreparedSilverWriteFinalizationContext:
        """Prepare DQ/version/timing context before Silver metadata persistence."""
        dq_metrics = await self._compute_dq_metrics(table_name, records)
        version_after = await self._get_delta_version(table_path)
        completed_at = started_at + timedelta(seconds=time.perf_counter() - start_perf)
        return _PreparedSilverWriteFinalizationContext(dq_metrics, version_after, completed_at)
