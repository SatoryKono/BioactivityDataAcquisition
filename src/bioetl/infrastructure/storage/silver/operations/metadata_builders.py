"""Pure helper functions for Silver metadata construction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import orjson

from bioetl.domain.models.metadata import (
    BaseOutputMetadata,
    ColumnMetrics,
    DeltaMetrics,
    DQSummary,
    EnvironmentMetadata,
    LineageMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    RunTypeEnum,
    SchemaDrift,
    SilverMetadata,
    SilverOutputExt,
)
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics


@dataclass(frozen=True, slots=True)
class _SilverMetadataBuildRequest:
    """Input bundle for constructing one SilverMetadata payload."""

    table_name: str
    table_path: str
    records: list[BronzeRecord]
    dq_metrics: BatchDQMetrics | None
    mode: str
    runtime_started_at: datetime
    runtime_completed_at: datetime
    run_id: RunID | str | None
    manifest_id: str | None
    run_type: RunType | object | None
    source_batch_id: BatchID | None
    transform_version: str | None
    transform_steps: tuple[str, ...] | None
    bronze_refs: list[BronzeWriteResult] | None
    primary_keys: list[str] | None = None
    version_after: int | None = None
    hostname: str = "localhost"
    bioetl_version: str = "test"
    python_version: str = "test"


def _split_table_name(table_name: str) -> tuple[str, str]:
    """Split a table name into provider/entity parts with safe fallbacks."""
    if "." in table_name:
        provider_name, entity_name = table_name.split(".", 1)
        return provider_name, entity_name
    return table_name, "unknown"


def _placeholder_table_path(table_name: str) -> str:
    """Build a stable placeholder path when the real table path is unavailable."""
    return f"data/output/silver/{table_name.replace('.', '/')}"


def _build_column_metrics_dict(
    dq_metrics: BatchDQMetrics | None,
) -> dict[str, ColumnMetrics]:
    """Convert DQ column stats into metadata-ready column metrics."""
    if not dq_metrics or not dq_metrics.column_stats:
        return {}
    return {
        col_name: col_stat.to_column_metrics()
        for col_name, col_stat in dq_metrics.column_stats.items()
    }


def _build_schema_drift_object(
    dq_metrics: BatchDQMetrics | None,
) -> SchemaDrift | None:
    """Convert DQ schema drift info into metadata-ready representation."""
    if not dq_metrics or not dq_metrics.schema_drift:
        return None
    return dq_metrics.schema_drift.to_schema_drift()


def _coerce_run_type(run_type: RunType | object | None) -> RunTypeEnum:
    """Normalize heterogeneous runtime run-type values to metadata enum."""
    if isinstance(run_type, RunTypeEnum):
        return run_type
    normalized = str(run_type or RunTypeEnum.INCREMENTAL).strip().lower()
    if normalized == RunTypeEnum.BACKFILL.value:
        return RunTypeEnum.BACKFILL
    if normalized == RunTypeEnum.REBUILD.value:
        return RunTypeEnum.REBUILD
    return RunTypeEnum.INCREMENTAL


def _coerce_delta_operation(
    mode: str,
) -> Literal["merge", "overwrite", "append"]:
    """Normalize write mode strings to the allowed Delta metadata literals."""
    normalized = mode.strip().lower()
    if normalized == "merge":
        return "merge"
    if normalized == "overwrite":
        return "overwrite"
    return "append"


def _resolve_dq_summary_values(
    dq_metrics: BatchDQMetrics | None,
    *,
    records_count: int,
) -> tuple[int, int, int, int, float, bool]:
    """Resolve DQ summary primitives with safe fallbacks for missing metrics."""
    if dq_metrics:
        total_records = dq_metrics.total_records
        valid_records = dq_metrics.valid_records
        error_records = dq_metrics.error_records
        warning_records = dq_metrics.warning_records or 0
        error_rate = (
            dq_metrics.error_records / dq_metrics.total_records
            if dq_metrics.total_records > 0
            else 0.0
        )
        validation_passed = dq_metrics.error_records == 0
        return (
            total_records,
            valid_records,
            error_records,
            warning_records,
            error_rate,
            validation_passed,
        )

    return (records_count, records_count, 0, 0, 0.0, True)


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


def _build_runtime_metadata(
    request: _SilverMetadataBuildRequest,
) -> RuntimeMetadata:
    """Build runtime metadata for a Silver sidecar."""
    return RuntimeMetadata(
        run_id=str(request.run_id or "unknown"),
        manifest_id=request.manifest_id,
        run_type=_coerce_run_type(request.run_type),
        started_at_utc=request.runtime_started_at,
        completed_at_utc=request.runtime_completed_at,
        duration_seconds=max(
            0,
            int(
                (
                    request.runtime_completed_at - request.runtime_started_at
                ).total_seconds()
            ),
        ),
    )


def _build_pipeline_metadata(provider_name: str, entity_name: str) -> PipelineMetadata:
    """Build pipeline identity metadata for a Silver sidecar."""
    return PipelineMetadata(
        name=provider_name,
        provider=provider_name,
        entity=entity_name,
        version="1.0",
    )


def _build_lineage_metadata(
    request: _SilverMetadataBuildRequest,
) -> LineageMetadata:
    """Build lineage metadata for a Silver sidecar."""
    return LineageMetadata(
        source_batch_ids=[str(request.source_batch_id)]
        if request.source_batch_id
        else [],
        bronze_paths=[ref.relative_path for ref in request.bronze_refs]
        if request.bronze_refs
        else [],
        transform_version=request.transform_version,
        transform_steps=list(request.transform_steps)
        if request.transform_steps
        else [],
    )


def _build_delta_metadata(request: _SilverMetadataBuildRequest) -> DeltaMetrics:
    """Build Delta operation metadata for a Silver sidecar."""
    return DeltaMetrics(
        table_path=request.table_path,
        operation=_coerce_delta_operation(request.mode),
        primary_key=request.primary_keys or [],
        partition_by=[],
        version_before=None,
        version_after=request.version_after,
        files_added=1,
        files_removed=0,
        rows_inserted=len(request.records),
        rows_updated=0,
        rows_deleted=0,
    )


def _build_dq_summary(request: _SilverMetadataBuildRequest) -> DQSummary:
    """Build DQ summary metadata for a Silver sidecar."""
    (
        total_records,
        valid_records,
        error_records,
        warning_records,
        error_rate,
        validation_passed,
    ) = _resolve_dq_summary_values(
        request.dq_metrics,
        records_count=len(request.records),
    )
    return DQSummary(
        total_records=total_records,
        valid_records=valid_records,
        error_records=error_records,
        warning_records=warning_records,
        error_rate=error_rate,
        column_metrics=_build_column_metrics_dict(request.dq_metrics),
        schema_drift=_build_schema_drift_object(request.dq_metrics),
        validation_passed=validation_passed,
    )


def _build_output_metadata(request: _SilverMetadataBuildRequest) -> BaseOutputMetadata:
    """Build output artifact metadata for a Silver sidecar."""
    return BaseOutputMetadata(
        artifact_id=f"{request.table_name}-{request.run_id or 'unknown'}",
        record_count=len(request.records),
        total_bytes=0,
        content_hash="placeholder-hash",
    )


def _build_environment_metadata(
    request: _SilverMetadataBuildRequest,
) -> EnvironmentMetadata:
    """Build runtime environment metadata for a Silver sidecar."""
    return EnvironmentMetadata(
        hostname=request.hostname,
        bioetl_version=request.bioetl_version,
        python_version=request.python_version,
    )


def _build_silver_metadata(
    request: _SilverMetadataBuildRequest,
) -> SilverMetadata:
    """Build a complete SilverMetadata payload from write/finalization inputs."""
    provider_name, entity_name = _split_table_name(request.table_name)
    return SilverMetadata(
        runtime=_build_runtime_metadata(request),
        pipeline=_build_pipeline_metadata(provider_name, entity_name),
        lineage=_build_lineage_metadata(request),
        delta=_build_delta_metadata(request),
        dq_summary=_build_dq_summary(request),
        output=_build_output_metadata(request),
        output_ext=SilverOutputExt(
            delta_version_before=None,
            delta_version_after=request.version_after,
        ),
        environment=_build_environment_metadata(request),
    )
