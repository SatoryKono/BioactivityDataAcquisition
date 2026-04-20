"""Pure helper functions for Silver metadata construction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import orjson

from bioetl.domain.models.metadata import SilverMetadata
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
) -> dict[str, object]:
    """Convert DQ column stats into metadata-ready column metrics."""
    if not dq_metrics or not dq_metrics.column_stats:
        return {}
    return {
        col_name: col_stat.to_column_metrics()
        for col_name, col_stat in dq_metrics.column_stats.items()
    }


def _build_schema_drift_object(dq_metrics: BatchDQMetrics | None) -> object | None:
    """Convert DQ schema drift info into metadata-ready representation."""
    if not dq_metrics or not dq_metrics.schema_drift:
        return None
    return dq_metrics.schema_drift.to_schema_drift()


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


def _build_silver_metadata(
    request: _SilverMetadataBuildRequest,
) -> SilverMetadata:
    """Build a complete SilverMetadata payload from write/finalization inputs."""
    from bioetl.domain.models.metadata import (
        BaseOutputMetadata,
        DeltaMetrics,
        DQSummary,
        EnvironmentMetadata,
        LineageMetadata,
        PipelineMetadata,
        RuntimeMetadata,
        SilverOutputExt,
    )

    provider_name, entity_name = _split_table_name(request.table_name)
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

    runtime_metadata = RuntimeMetadata(
        run_id=str(request.run_id or "unknown"),
        manifest_id=request.manifest_id,
        run_type=request.run_type or "incremental",
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
    pipeline_metadata = PipelineMetadata(
        name=provider_name,
        provider=provider_name,
        entity=entity_name,
        version="1.0",
    )
    lineage_metadata = LineageMetadata(
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
    delta_metadata = DeltaMetrics(
        table_path=request.table_path,
        operation=str(request.mode),
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
    dq_summary = DQSummary(
        total_records=total_records,
        valid_records=valid_records,
        error_records=error_records,
        warning_records=warning_records,
        error_rate=error_rate,
        column_metrics=_build_column_metrics_dict(request.dq_metrics),
        schema_drift=_build_schema_drift_object(request.dq_metrics),
        validation_passed=validation_passed,
    )
    return SilverMetadata(
        table_name=request.table_name,
        runtime=runtime_metadata,
        pipeline=pipeline_metadata,
        lineage=lineage_metadata,
        delta=delta_metadata,
        dq_summary=dq_summary,
        output=BaseOutputMetadata(
            artifact_id=f"{request.table_name}-{request.run_id or 'unknown'}",
            record_count=len(request.records),
            total_bytes=0,
            content_hash="placeholder-hash",
        ),
        output_ext=SilverOutputExt(
            delta_version_before=None,
            delta_version_after=request.version_after,
        ),
        environment=EnvironmentMetadata(
            hostname=request.hostname,
            bioetl_version=request.bioetl_version,
            python_version=request.python_version,
        ),
    )
