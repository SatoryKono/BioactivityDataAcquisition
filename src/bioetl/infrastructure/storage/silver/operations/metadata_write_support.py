"""Write/audit helpers for composition-backed Silver metadata operations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, cast

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.ports import (
    AuditPort,
    LoggerPort,
    MetadataCoordinatorPort,
    MetricsPort,
    SilverMetadataInput,
)
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.metadata.builder_base import (
    _resolve_metadata_timestamp,
)


class _MetadataWriteOps(Protocol):
    """Minimal host surface needed by Silver metadata write helpers."""

    @property
    def _metrics(self) -> MetricsPort | None: ...

    @property
    def _audit(self) -> AuditPort | None: ...

    @property
    def _metadata_coordinator(self) -> MetadataCoordinatorPort | None: ...

    async def _persist_silver_metadata(
        self,
        *,
        metadata: SilverMetadata,
        table_name: str,
        table_path: str,
    ) -> SilverWriteResult | None: ...


class _MetadataAuditOps(Protocol):
    """Minimal host surface needed by Silver audit helpers."""

    @property
    def _audit(self) -> AuditPort | None: ...


class _SilverAuditHost:
    """Simple audit host adapter exposing the logger expected by audit builders."""

    def __init__(self, logger: LoggerPort) -> None:
        self.logger = logger


def _resolve_metadata_logger(metadata_ops: object) -> LoggerPort:
    """Resolve logger from either composition or mixin style host objects."""
    logger = getattr(metadata_ops, "_logger", None)
    if logger is None:
        logger = getattr(metadata_ops, "logger", None)
    if logger is None:
        raise AttributeError(
            "Silver metadata audit host must expose either '_logger' or 'logger'"
        )
    return cast(LoggerPort, logger)


@dataclass(frozen=True, slots=True)
class _SilverMetadataWriteSupportRequest:
    """Normalized support-layer request for one Silver metadata sidecar write."""

    table_name: str
    dq_metrics: BatchDQMetrics
    records: list[BronzeRecord]
    bronze_refs: list[BronzeWriteResult] | None = None
    mode: str = "merge"
    validated_mode: SilverWriteMode = SilverWriteMode.MERGE
    run_id: RunID | None = None
    run_type: RunType | None = None
    source_batch_id: BatchID | None = None
    ingestion_ts: datetime | None = None
    transform_version: str | None = None
    transform_steps: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class _SilverMetadataAuditSupportRequest:
    """Normalized support-layer request for one Silver audit write."""

    table_name: str
    records: list[BronzeRecord]
    mode: SilverWriteMode
    run_id: RunID | None = None
    run_type: RunType | None = None
    source_batch_id: BatchID | None = None
    ingestion_ts: datetime | None = None


_AUDIT_SUPPORT_FIELDS = (
    "table_name",
    "records",
    "mode",
    "run_id",
    "run_type",
    "source_batch_id",
    "ingestion_ts",
)
_AUDIT_SUPPORT_REQUIRED_FIELDS = (
    "table_name",
    "records",
    "mode",
)
_AUDIT_SUPPORT_DEFAULTS: dict[str, object] = {
    "run_id": None,
    "run_type": None,
    "source_batch_id": None,
    "ingestion_ts": None,
}
_METRIC_LABEL_SANITIZER = re.compile(r"[^a-z0-9_]+")


def _fallback_table_path(table_name: str) -> str:
    """Build a deterministic Silver sidecar path for support-level writes."""
    return f"data/output/silver/{str(table_name).replace('.', '/')}"


def _normalize_metric_label(value: object, *, fallback: str) -> str:
    """Normalize free-form storage identifiers to bounded metric label values."""
    normalized = _METRIC_LABEL_SANITIZER.sub(
        "_",
        str(value or "").strip().lower(),
    ).strip("_")
    return normalized or fallback


def _silver_metadata_write_success_labels(table_name: str) -> dict[str, str]:
    """Build canonical labels for successful Silver metadata sidecar writes."""
    table_parts = [part for part in str(table_name or "").split(".") if part]
    provider = (
        _normalize_metric_label(table_parts[0], fallback="storage")
        if len(table_parts) >= 2
        else "storage"
    )
    pipeline_source = "_".join(table_parts) if table_parts else table_name
    return {
        "layer": "silver",
        "provider": provider,
        "pipeline": _normalize_metric_label(
            pipeline_source,
            fallback="silver_metadata",
        ),
        "status": "success",
        "final_reason": "completed",
    }


def _require_metadata_coordinator(
    metadata_ops: _MetadataWriteOps,
) -> MetadataCoordinatorPort:
    """Resolve the canonical metadata coordinator for Silver sidecar writes."""
    coordinator = metadata_ops._metadata_coordinator
    if coordinator is None:
        raise RuntimeError(
            "MetadataCoordinatorPort is required for Silver metadata publication"
        )
    return coordinator


def _source_batch_ids(source_batch_id: BatchID | None) -> list[str] | None:
    """Normalize optional source batch identity for SilverMetadataInput."""
    if source_batch_id is None:
        return None
    return [str(source_batch_id)]


def _coerce_silver_metadata_audit_request(
    request: _SilverMetadataAuditSupportRequest | None = None,
    *,
    args: tuple[object, ...] = (),
    kwargs: dict[str, object] | None = None,
) -> _SilverMetadataAuditSupportRequest:
    """Normalize legacy or request-style Silver audit arguments."""
    if isinstance(request, _SilverMetadataAuditSupportRequest):
        if args or kwargs:
            raise TypeError(
                "_SilverMetadataAuditSupportRequest cannot be combined with "
                "legacy args/kwargs"
            )
        return request

    resolved_kwargs = dict(kwargs or {})
    legacy_values = list(args) if request is None else [request, *args]
    if len(legacy_values) > len(_AUDIT_SUPPORT_FIELDS):
        raise TypeError("_log_silver_audit() received too many positional arguments")

    for field_name, value in zip(_AUDIT_SUPPORT_FIELDS, legacy_values, strict=False):
        if field_name in resolved_kwargs:
            raise TypeError(
                f"_log_silver_audit() got multiple values for argument '{field_name}'"
            )
        resolved_kwargs[field_name] = value

    unexpected_fields = sorted(
        set(resolved_kwargs)
        - frozenset({*_AUDIT_SUPPORT_FIELDS, *tuple(_AUDIT_SUPPORT_DEFAULTS)})
    )
    if unexpected_fields:
        unexpected = ", ".join(unexpected_fields)
        raise TypeError(
            f"_log_silver_audit() got unexpected keyword arguments: {unexpected}"
        )

    missing_fields = [
        field_name
        for field_name in _AUDIT_SUPPORT_REQUIRED_FIELDS
        if field_name not in resolved_kwargs
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise TypeError(f"_log_silver_audit() missing required arguments: {missing}")

    for field_name, default in _AUDIT_SUPPORT_DEFAULTS.items():
        resolved_kwargs.setdefault(field_name, default)

    return _SilverMetadataAuditSupportRequest(
        table_name=resolved_kwargs["table_name"],  # type: ignore[arg-type]
        records=resolved_kwargs["records"],  # type: ignore[arg-type]
        mode=resolved_kwargs["mode"],  # type: ignore[arg-type]
        run_id=resolved_kwargs["run_id"],  # type: ignore[arg-type]
        run_type=resolved_kwargs["run_type"],  # type: ignore[arg-type]
        source_batch_id=resolved_kwargs["source_batch_id"],  # type: ignore[arg-type]
        ingestion_ts=resolved_kwargs["ingestion_ts"],  # type: ignore[arg-type]
    )


async def _write_silver_metadata(
    metadata_ops: _MetadataWriteOps,
    request: _SilverMetadataWriteSupportRequest,
) -> SilverWriteResult | None:
    """Write one Silver metadata sidecar through the canonical coordinator port."""
    coordinator = _require_metadata_coordinator(metadata_ops)
    runtime_anchor = _resolve_metadata_timestamp(
        explicit=request.ingestion_ts,
        records=request.records,
    )
    table_path_placeholder = _fallback_table_path(request.table_name)
    metadata = coordinator.create_silver_metadata(
        SilverMetadataInput(
            table_path=table_path_placeholder,
            primary_keys=[],
            mode=request.validated_mode,
            records=request.records,
            total_records=len(request.records),
            source_batch_ids=_source_batch_ids(request.source_batch_id),
            bronze_refs=request.bronze_refs,
            dq_metrics=request.dq_metrics,
            transform_version=request.transform_version,
            transform_steps=request.transform_steps,
            started_at=runtime_anchor,
            completed_at=runtime_anchor,
        )
    )
    result = await metadata_ops._persist_silver_metadata(
        metadata=metadata,
        table_name=request.table_name,
        table_path=table_path_placeholder,
    )
    _emit_silver_metadata_write_success(
        metadata_ops,
        request.table_name,
        request.records,
        request.dq_metrics,
        timestamp=runtime_anchor,
    )
    return result


def _emit_silver_metadata_write_success(
    metadata_ops: _MetadataWriteOps,
    table_name: str,
    records: list[BronzeRecord],
    dq_metrics: BatchDQMetrics,
    *,
    timestamp: datetime | None,
) -> None:
    """Emit success metrics and audit for one Silver metadata write."""
    if metadata_ops._metrics:
        metadata_ops._metrics.increment_counter(
            "bioetl_metadata_write_outcomes_total",
            1,
            _silver_metadata_write_success_labels(table_name),
        )

    if metadata_ops._audit:
        metadata_ops._audit.log_event(
            "SilverMetadataWrite",
            {
                "table": table_name,
                "records": len(records),
                "dq_metrics": dq_metrics.dict()
                if hasattr(dq_metrics, "dict")
                else str(dq_metrics),
                "status": "success",
            },
            timestamp=_resolve_metadata_timestamp(explicit=timestamp, records=records),
        )


async def _log_silver_audit_event(
    metadata_ops: _MetadataAuditOps,
    request: _SilverMetadataAuditSupportRequest,
) -> None:
    """Build and persist one Silver audit entry."""
    if not metadata_ops._audit:
        return

    from bioetl.infrastructure.storage.silver.audit_operations import (
        _build_silver_audit_entry,
        _SilverAuditWriteRequest,
    )

    audit_write_request: _SilverAuditWriteRequest = _SilverAuditWriteRequest(
        table_name=request.table_name,
        records=request.records,
        mode=request.mode,
        run_id=request.run_id,
        run_type=request.run_type,
        source_batch_id=request.source_batch_id,
        ingestion_ts=request.ingestion_ts,
    )
    audit_entry = _build_silver_audit_entry(
        _SilverAuditHost(_resolve_metadata_logger(metadata_ops)),
        audit_write_request,
    )
    await metadata_ops._audit.log_write(audit_entry)
