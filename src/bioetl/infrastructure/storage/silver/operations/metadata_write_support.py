"""Write/audit helpers for composition-backed Silver metadata operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, cast

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.ports import AuditPort, LoggerPort, MetricsPort
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.metadata.builder_base import (
    _resolve_metadata_timestamp,
)
from bioetl.infrastructure.storage.silver.operations.metadata_sidecar_adapter import (
    _build_silver_sidecar_metadata,
    _fallback_table_path,
    _SilverMetadataSidecarRequest,
    extract_control_plane_provenance_from_records,
)


class _MetadataWriteOps(Protocol):
    """Minimal host surface needed by Silver metadata write helpers."""

    @property
    def _metrics(self) -> MetricsPort | None: ...

    @property
    def _audit(self) -> AuditPort | None: ...

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
    """Write one Silver metadata sidecar through the configured writer."""
    _ = request.validated_mode

    runtime_anchor = _resolve_metadata_timestamp(
        explicit=request.ingestion_ts,
        records=request.records,
    )
    table_path_placeholder = _fallback_table_path(request.table_name)
    provenance = extract_control_plane_provenance_from_records(request.records)
    metadata = _build_silver_sidecar_metadata(
        _SilverMetadataSidecarRequest(
            table_name=request.table_name,
            table_path=table_path_placeholder,
            records=request.records,
            dq_metrics=request.dq_metrics,
            mode=request.mode,
            runtime_started_at=runtime_anchor,
            runtime_completed_at=runtime_anchor,
            run_id=request.run_id,
            manifest_id=(
                str(request.records[0]["_manifest_id"])
                if request.records
                and request.records[0].get("_manifest_id") is not None
                else None
            ),
            run_type=request.run_type,
            source_batch_id=request.source_batch_id,
            transform_version=request.transform_version,
            transform_steps=request.transform_steps,
            bronze_refs=request.bronze_refs,
            execution_fingerprint=provenance["execution_fingerprint"],
            config_hash=provenance["config_hash"],
            resolved_config_hash=provenance["resolved_config_hash"],
            effective_config_hash=provenance["effective_config_hash"],
            effective_config_artifact_id=provenance["effective_config_artifact_id"],
            contract_ref=provenance["contract_ref"],
            contract_version=provenance["contract_version"],
            contract_schema_hash=provenance["contract_schema_hash"],
            dq_policy_ref=provenance["dq_policy_ref"],
            rule_bundle_version=provenance["rule_bundle_version"],
            dq_contract_compatibility_hash=provenance[
                "dq_contract_compatibility_hash"
            ],
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
        metadata_ops._metrics.increment_counter("silver.metadata_write_success", 1)

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
