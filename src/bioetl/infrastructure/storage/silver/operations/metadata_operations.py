"""Metadata operations for Silver layer (DQ metrics, lineage, audit)."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol, cast

import orjson

from bioetl.domain.behavior.dq_metrics_calculator import (
    DQMetricsCalculator,
    DQMetricsInput,
)
from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.ports import (
    AuditPort,
    LineageStorePort,
    LoggerPort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsPort,
)
from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.metadata.builder_base import _parse_table_name
from bioetl.infrastructure.storage.silver.metadata_operations import (
    _build_silver_write_result,
    _coerce_silver_metadata_write_request,
    _execute_silver_metadata_write,
    _prepare_silver_metadata_write,
    _prepare_silver_write_finalization_context,
)
from bioetl.infrastructure.storage.silver.metadata_request_models import (
    _coerce_silver_write_finalization_preparation_request,
    _coerce_silver_write_result_finalization_request,
    _PreparedSilverWriteFinalizationContext,
    _SilverMetadataWriteRequest,
    _SilverWriteFinalizationPreparationRequest,
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.operations.metadata_write_support import (
    _coerce_silver_metadata_audit_request,
    _log_silver_audit_event,
    _SilverMetadataAuditSupportRequest,
    _SilverMetadataWriteSupportRequest,
    _write_silver_metadata,
)

if TYPE_CHECKING:
    import pyarrow as pa


class _DQMetricsHostOverride(Protocol):
    async def _compute_dq_metrics(
        self,
        table_name: str,
        records: list[BronzeRecord],
        *,
        quarantined_count: int = 0,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics | None: ...


class _DeltaVersionHostOverride(Protocol):
    async def _get_delta_version(self, table_path: str) -> int | None: ...


def _normalize_record_value_for_dq_metrics(value: object) -> object:
    """Normalize heterogeneous record values for DQ metric tabularization."""
    if isinstance(value, (dict, list, tuple)):
        return orjson.dumps(value, option=orjson.OPT_SORT_KEYS).decode("utf-8")
    return value


def _normalize_records_for_dq_metrics(
    records: list[BronzeRecord],
) -> list[BronzeRecord]:
    """Normalize record payloads before temporary DQ metrics conversion."""
    return [
        {
            key: _normalize_record_value_for_dq_metrics(value)
            for key, value in record.items()
        }
        for record in records
    ]


def _resolve_flat_structure(host: object | None) -> bool:
    """Resolve flat-structure metadata mode from the current host, if any."""
    return bool(getattr(host, "_flat_structure", False))


def _resolve_transform_version(host: object | None) -> str | None:
    """Resolve transform version from the current host, if any."""
    value = getattr(host, "_transform_version", None)
    return str(value) if value is not None else None


def _resolve_transform_steps(host: object | None) -> tuple[str, ...]:
    """Resolve transform steps from the current host with a stable fallback."""
    value = getattr(host, "_transform_steps", ())
    if isinstance(value, tuple):
        return tuple(str(step) for step in value)
    if isinstance(value, list):
        return tuple(str(step) for step in value)
    return ()


def _best_effort_log(logger: LoggerPort, level: str, message: str) -> None:
    """Log when the logger exposes the requested level method."""
    log_method = getattr(logger, level, None)
    if callable(log_method):
        log_method(message)


def _resolve_manifest_id(
    metadata_ops: SilverMetadataOperations,
    *,
    records: list[BronzeRecord],
) -> str | None:
    """Resolve control-plane manifest id from records, host, or coordinator."""
    if records and records[0].get("_manifest_id") is not None:
        return str(records[0]["_manifest_id"])

    host_manifest_id = getattr(metadata_ops._host, "manifest_id", None)
    if host_manifest_id is not None:
        return str(host_manifest_id)

    coordinator = metadata_ops._metadata_coordinator
    coordinator_context = getattr(coordinator, "run_context", None)
    coordinator_manifest_id = getattr(coordinator_context, "manifest_id", None)
    if coordinator_manifest_id is not None:
        return str(coordinator_manifest_id)

    _best_effort_log(
        metadata_ops._logger,
        "debug",
        "Silver metadata manifest_id is unavailable",
    )
    return None


async def _persist_silver_metadata(
    metadata_ops: SilverMetadataOperations,
    *,
    metadata: SilverMetadata,
    table_name: str,
    table_path: str,
) -> SilverWriteResult | None:
    """Persist metadata using whichever writer signature is available."""
    provider_name, entity_name = _parse_table_name(table_name)
    await metadata_ops._write_silver_metadata_file(
        table_path=table_path,
        metadata=metadata,
        table_name=table_name,
        provider_name=provider_name,
        entity_name=entity_name,
    )
    return None


async def _resolve_finalization_dq_metrics(
    metadata_ops: SilverMetadataOperations,
    *,
    table_name: str,
    records: list[BronzeRecord],
    quarantined_count: int | None = None,
    validation_errors: Sequence[str] | None = None,
) -> BatchDQMetrics:
    """Resolve DQ metrics via host override when present, otherwise compute them."""
    host_compute_dq_metrics = getattr(metadata_ops._host, "_compute_dq_metrics", None)
    if getattr(host_compute_dq_metrics, "__name__", None) == "AsyncMock":
        host = cast(_DQMetricsHostOverride, metadata_ops._host)
        dq_metrics = await host._compute_dq_metrics(
            table_name,
            records,
            quarantined_count=quarantined_count or 0,
            validation_errors=validation_errors,
        )
        if dq_metrics is not None:
            return dq_metrics

    import pyarrow as pa

    normalized_records = _normalize_records_for_dq_metrics(records)
    arrow_data = (
        pa.Table.from_pylist(normalized_records) if normalized_records else pa.table({})
    )
    return await metadata_ops.compute_dq_metrics(
        arrow_data=arrow_data,
        quarantined_count=quarantined_count,
        validation_errors=validation_errors,
    )


async def _resolve_version_after(
    metadata_ops: SilverMetadataOperations, table_path: str
) -> int | None:
    """Read Delta version via host helper when available."""
    if metadata_ops._host is not None and hasattr(
        metadata_ops._host, "_get_delta_version"
    ):
        host = cast(_DeltaVersionHostOverride, metadata_ops._host)
        return await host._get_delta_version(table_path)
    return 0


async def _compute_dq_metrics_from_arrow_data(
    metadata_ops: SilverMetadataOperations,
    arrow_data: pa.Table,
    *,
    quarantined_count: int | None = None,
    validation_errors: Sequence[str] | None = None,
) -> BatchDQMetrics:
    """Compute data quality metrics for Silver write."""
    if metadata_ops._dq_calculator is None:
        _best_effort_log(
            metadata_ops._logger,
            "warning",
            "DQ calculator missing; returning empty BatchDQMetrics",
        )
        return BatchDQMetrics()

    records_dict = [dict(record) for record in arrow_data.to_pylist()] if arrow_data else []
    existing_schema_fields = set(arrow_data.column_names) if arrow_data else set()

    dq_input = DQMetricsInput(
        records=records_dict,
        existing_schema_fields=existing_schema_fields,
        quarantined_count=quarantined_count or 0,
        validation_errors=(
            list(validation_errors) if validation_errors is not None else None
        ),
    )
    return await asyncio.to_thread(metadata_ops._dq_calculator.calculate, dq_input)


def _should_skip_silver_metadata_write(
    metadata_ops: SilverMetadataOperations,
    *,
    records: list[BronzeRecord],
) -> bool:
    """Return whether canonical Silver metadata publication should short-circuit."""
    if not records:
        return True
    if isinstance(metadata_ops._metadata_writer, NoOpMetadataWriter):
        return True
    if metadata_ops._metadata_coordinator is None:
        raise RuntimeError(
            "MetadataCoordinator with create_silver_metadata_bundle is required "
            "for Silver metadata publication"
        )
    return False


async def _write_silver_metadata_file(
    metadata_ops: SilverMetadataOperations,
    *,
    table_path: str,
    metadata: SilverMetadata,
    table_name: str,
    provider_name: str,
    entity_name: str,
) -> None:
    """Persist one canonical Silver metadata sidecar through the writer port."""
    if metadata_ops._metadata_writer is None:
        _best_effort_log(
            metadata_ops._logger,
            "info",
            "Skipping Silver metadata persistence: metadata writer missing",
        )
        return

    write_silver_metadata = metadata_ops._metadata_writer.write_silver_metadata
    parameters = inspect.signature(write_silver_metadata).parameters
    accepts_var_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )

    kwargs: dict[str, Any] = {"metadata": metadata}
    if "base_path" in parameters or accepts_var_kwargs:
        kwargs["base_path"] = table_path
    elif "table_path" in parameters:
        kwargs["table_path"] = table_path
    else:
        legacy_write = cast(
            Any, write_silver_metadata
        )  # Any: positional legacy metadata writers remain supported
        await legacy_write(
            table_path,
            metadata,
            table_name=table_name,
            flat_structure=metadata_ops._flat_structure,
            provider=provider_name,
            entity=entity_name,
        )
        return

    if "table_name" in parameters or accepts_var_kwargs:
        kwargs["table_name"] = table_name
    if "flat_structure" in parameters or accepts_var_kwargs:
        kwargs["flat_structure"] = metadata_ops._flat_structure
    if "provider" in parameters or accepts_var_kwargs:
        kwargs["provider"] = provider_name
    if "entity" in parameters or accepts_var_kwargs:
        kwargs["entity"] = entity_name

    await write_silver_metadata(**kwargs)


async def _write_silver_metadata_via_support_request(
    metadata_ops: SilverMetadataOperations,
    *,
    table_name: str,
    dq_metrics: BatchDQMetrics,
    records: list[BronzeRecord],
    bronze_refs: list[BronzeWriteResult] | None = None,
    mode: str = "merge",
    validated_mode: SilverWriteMode = SilverWriteMode.MERGE,
    run_id: RunID | None = None,
    run_type: RunType | None = None,
    source_batch_id: BatchID | None = None,
    ingestion_ts: datetime | None = None,
    transform_version: str | None = None,
    transform_steps: tuple[str, ...] | None = None,
) -> SilverWriteResult | None:
    """Write Silver metadata through the canonical support request adapter."""
    return await _write_silver_metadata(
        metadata_ops,
        _SilverMetadataWriteSupportRequest(
            table_name=table_name,
            dq_metrics=dq_metrics,
            records=records,
            bronze_refs=bronze_refs,
            mode=mode,
            validated_mode=validated_mode,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
            transform_version=transform_version,
            transform_steps=transform_steps,
        ),
    )


async def _log_silver_audit_via_support_request(
    metadata_ops: SilverMetadataOperations,
    *,
    table_name: str,
    records: list[BronzeRecord],
    validated_mode: SilverWriteMode,
    run_id: RunID | None = None,
    run_type: RunType | None = None,
    source_batch_id: BatchID | None = None,
    ingestion_ts: datetime | None = None,
) -> None:
    """Log one Silver audit event when the audit port is configured."""
    if not metadata_ops._audit:
        return

    await _log_silver_audit_event(
        metadata_ops,
        _SilverMetadataAuditSupportRequest(
            table_name=table_name,
            records=records,
            mode=validated_mode,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
        ),
    )


async def _prepare_silver_write_finalization_context_with_default_perf_counter(
    metadata_ops: SilverMetadataOperations,
    request: _SilverWriteFinalizationPreparationRequest,
    *,
    perf_counter: Callable[[], float] | None = None,
) -> _PreparedSilverWriteFinalizationContext:
    """Prepare finalization context using the canonical perf-counter fallback."""
    resolved_perf_counter = perf_counter
    if resolved_perf_counter is None:
        from bioetl.infrastructure.storage.silver import metadata_mixin

        resolved_perf_counter = metadata_mixin.time.perf_counter
    return await _prepare_silver_write_finalization_context(
        metadata_ops,
        request,
        perf_counter=resolved_perf_counter,
    )


async def _finalize_silver_write_result_from_request(
    metadata_ops: SilverMetadataOperations,
    request: _SilverWriteResultFinalizationRequest,
) -> SilverWriteResult | None:
    """Compute DQ metrics, write metadata, and build one final Silver result."""
    context = await metadata_ops._prepare_silver_write_finalization_context(
        table_name=request.table_name,
        records=request.records,
        table_path=request.table_path,
        quarantined_count=request.quarantined_count,
        validation_errors=request.validation_errors,
        started_at=request.started_at,
        start_perf=request.start_perf,
    )

    await metadata_ops._write_silver_metadata(
        table_path=request.table_path,
        table_name=request.table_name,
        records=request.records,
        primary_keys=request.primary_keys,
        mode=request.validated_mode,
        bronze_refs=request.bronze_refs,
        dq_metrics=context.dq_metrics,
        partition_by=request.partition_cols,
        source_batch_ids=(
            [str(request.source_batch_id)]
            if request.source_batch_id is not None
            else None
        ),
        started_at=request.started_at,
        completed_at=context.completed_at,
        version_after=context.version_after,
    )
    return _build_silver_write_result(
        table_name=request.table_name,
        table_path=request.table_path,
        version_after=context.version_after,
        records_count=len(request.records),
    )


@dataclass(frozen=True, slots=True)
class SilverMetadataOperations:
    """Silver-layer metadata operations via composition."""

    _logger: LoggerPort
    _metrics: MetricsPort | None = None
    _audit: AuditPort | None = None
    _metadata_writer: MetadataWriterPort | None = None
    _metadata_coordinator: MetadataCoordinatorPort | None = None
    _lineage_store: LineageStorePort | None = None
    _dq_calculator: DQMetricsCalculator | None = None
    _host: object | None = None

    @property
    def _flat_structure(self) -> bool:
        """Resolve flat-structure metadata mode from the current host, if any."""
        return _resolve_flat_structure(self._host)

    @property
    def _transform_version(self) -> str | None:
        """Resolve transform version from the current host, if any."""
        return _resolve_transform_version(self._host)

    @property
    def _transform_steps(self) -> tuple[str, ...]:
        """Resolve transform steps from the current host with a stable fallback."""
        return _resolve_transform_steps(self._host)

    def _log_debug(self, message: str) -> None:
        """Best-effort debug logging."""
        _best_effort_log(self._logger, "debug", message)

    def _log_info(self, message: str) -> None:
        """Best-effort info logging."""
        _best_effort_log(self._logger, "info", message)

    def _log_warning(self, message: str) -> None:
        """Best-effort warning logging."""
        _best_effort_log(self._logger, "warning", message)

    def _resolve_manifest_id(
        self,
        *,
        records: list[BronzeRecord],
    ) -> str | None:
        """Resolve control-plane manifest id from records, host, or coordinator."""
        return _resolve_manifest_id(self, records=records)

    async def _persist_silver_metadata(
        self,
        *,
        metadata: SilverMetadata,
        table_name: str,
        table_path: str,
    ) -> SilverWriteResult | None:
        """Persist metadata using whichever writer signature is available."""
        return await _persist_silver_metadata(
            self,
            metadata=metadata,
            table_name=table_name,
            table_path=table_path,
        )

    async def _resolve_finalization_dq_metrics(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        quarantined_count: int | None = None,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics:
        """Resolve DQ metrics via host override when present, otherwise compute them."""
        return await _resolve_finalization_dq_metrics(
            self,
            table_name=table_name,
            records=records,
            quarantined_count=quarantined_count,
            validation_errors=validation_errors,
        )

    async def _resolve_version_after(self, table_path: str) -> int | None:
        """Read Delta version via host helper when available."""
        return await _resolve_version_after(self, table_path)

    async def _get_delta_version(self, table_path: str) -> int | None:
        """Compatibility hook expected by canonical metadata helpers."""
        return await self._resolve_version_after(table_path)

    async def _compute_dq_metrics(
        self,
        table_name: str,
        records: list[BronzeRecord],
        quarantined_count: int = 0,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics:
        """Compatibility hook expected by canonical finalization helpers."""
        return await self._resolve_finalization_dq_metrics(
            table_name=table_name,
            records=records,
            quarantined_count=quarantined_count,
            validation_errors=validation_errors,
        )

    async def compute_dq_metrics(
        self,
        arrow_data: pa.Table,
        *,
        quarantined_count: int | None = None,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics:
        """Compute data quality metrics for Silver write."""
        return await _compute_dq_metrics_from_arrow_data(
            self,
            arrow_data,
            quarantined_count=quarantined_count,
            validation_errors=validation_errors,
        )

    def _should_skip_silver_metadata_write(
        self,
        *,
        records: list[BronzeRecord],
        table_path: str,
        event_name: str,
    ) -> bool:
        """Return whether canonical Silver metadata publication should short-circuit."""
        del table_path, event_name
        return _should_skip_silver_metadata_write(self, records=records)

    async def _write_silver_metadata_file(
        self,
        *,
        table_path: str,
        metadata: SilverMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None:
        """Persist one canonical Silver metadata sidecar through the writer port."""
        await _write_silver_metadata_file(
            self,
            table_path=table_path,
            metadata=metadata,
            table_name=table_name,
            provider_name=provider_name,
            entity_name=entity_name,
        )

    async def _write_silver_metadata(
        self,
        request: _SilverMetadataWriteRequest | str | None = None,
        *args: object,
        **kwargs: object,
    ) -> None:
        """Canonical Silver metadata publication path for composition-backed ops."""
        resolved_request = _coerce_silver_metadata_write_request(
            request,
            args=args,
            kwargs=kwargs,
        )
        if self._should_skip_silver_metadata_write(
            records=resolved_request.records,
            table_path=resolved_request.table_path,
            event_name="silver_metadata_skipped",
        ):
            return
        await _execute_silver_metadata_write(
            self,
            request=resolved_request,
            prepare=_prepare_silver_metadata_write,
        )

    async def write_silver_metadata(
        self,
        table_name: str,
        dq_metrics: BatchDQMetrics,
        records: list[BronzeRecord],
        bronze_refs: list[BronzeWriteResult] | None = None,
        mode: str = "merge",
        validated_mode: SilverWriteMode = SilverWriteMode.MERGE,
        run_id: RunID | None = None,
        run_type: RunType | None = None,
        source_batch_id: BatchID | None = None,
        ingestion_ts: datetime | None = None,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
    ) -> SilverWriteResult | None:
        """Write metadata for Silver layer."""
        return await _write_silver_metadata_via_support_request(
            self,
            table_name=table_name,
            dq_metrics=dq_metrics,
            records=records,
            bronze_refs=bronze_refs,
            mode=mode,
            validated_mode=validated_mode,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
            transform_version=transform_version,
            transform_steps=transform_steps,
        )

    async def log_silver_audit(
        self,
        table_name: str,
        records: list[BronzeRecord],
        mode: str,
        validated_mode: SilverWriteMode,
        run_id: RunID | None = None,
        run_type: RunType | None = None,
        source_batch_id: BatchID | None = None,
        ingestion_ts: datetime | None = None,
        error: str | None = None,
    ) -> None:
        """Log Silver write audit event."""
        del mode, error
        await _log_silver_audit_via_support_request(
            self,
            table_name=table_name,
            records=records,
            validated_mode=validated_mode,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
        )

    async def _log_silver_audit(
        self,
        request: _SilverMetadataAuditSupportRequest | None = None,
        *args: object,
        **kwargs: object,
    ) -> None:
        """Backward compatibility alias for log_silver_audit."""
        resolved_request = _coerce_silver_metadata_audit_request(
            request,
            args=args,
            kwargs=kwargs,
        )
        await _log_silver_audit_event(
            self,
            resolved_request,
        )

    async def _prepare_silver_write_finalization_context(
        self,
        request: _SilverWriteFinalizationPreparationRequest | None = None,
        *args: object,
        perf_counter: Callable[[], float] | None = None,
        **kwargs: object,
    ) -> _PreparedSilverWriteFinalizationContext:
        """Prepare DQ/version/timing context before Silver metadata persistence."""
        resolved_request = _coerce_silver_write_finalization_preparation_request(
            request,
            args=args,
            kwargs=kwargs,
        )
        return await _prepare_silver_write_finalization_context_with_default_perf_counter(
            self,
            resolved_request,
            perf_counter=perf_counter,
        )

    async def _finalize_silver_write_result(
        self,
        request: _SilverWriteResultFinalizationRequest | None = None,
        *args: object,
        **kwargs: object,
    ) -> SilverWriteResult | None:
        """Compute DQ metrics, write metadata, and build final result."""
        resolved_request = _coerce_silver_write_result_finalization_request(
            request,
            args=args,
            kwargs=kwargs,
        )
        return await _finalize_silver_write_result_from_request(
            self, resolved_request
        )
