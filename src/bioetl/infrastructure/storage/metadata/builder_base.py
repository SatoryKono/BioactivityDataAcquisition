"""Shared base helpers for metadata builders."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from platform import node as hostname
from platform import python_version
from typing import TYPE_CHECKING

from bioetl import __version__ as BIOETL_VERSION
from bioetl.domain.behavior.composite_metadata_helpers import (
    summarize_composite_cv_dq,
)
from bioetl.domain.lineage import DatasetRef
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import (
        DQSummary,
        EnvironmentMetadata,
        LineageMetadata,
        PipelineMetadata,
        RuntimeMetadata,
    )


def _get_git_commit_cached() -> str | None:
    """Get git commit hash directly via subprocess."""
    import subprocess
    from shutil import which

    git_executable = which("git")
    if not git_executable:
        return None

    try:
        result = subprocess.run(  # nosec B603 - Git path resolved via which()
            [git_executable, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,  # Local git subprocess — 5s is generous
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def _parse_table_name(table_name: str) -> tuple[str, str]:
    """Parse table name into provider and entity components."""
    if "." in table_name:
        parts = table_name.split(".")
        return parts[0], parts[1] if len(parts) > 1 else parts[0]
    if "/" in table_name:
        parts = table_name.split("/")
        return (parts[0] if len(parts) > 1 else "composite"), parts[-1]
    if "_" in table_name:
        parts = table_name.split("_", 1)
        return parts[0], parts[1] if len(parts) > 1 else parts[0]
    return "unknown", table_name if table_name else "unknown"


def _normalize_metadata_timestamp(value: datetime) -> datetime:
    """Return a stable UTC-aware metadata timestamp."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_record_timestamp(value: object) -> datetime | None:
    """Parse one record-level timestamp candidate."""
    if isinstance(value, datetime):
        return _normalize_metadata_timestamp(value)
    if isinstance(value, str):
        try:
            return _normalize_metadata_timestamp(datetime.fromisoformat(value))
        except ValueError:
            return None
    return None


def _resolve_records_metadata_timestamp(
    records: Sequence[Mapping[str, object]],
) -> datetime | None:
    """Resolve a deterministic timestamp anchor from persisted record metadata."""
    candidates: list[datetime] = []
    for record in records:
        for field_name in ("_lineage_created_at", "_ingestion_ts"):
            parsed = _parse_record_timestamp(record.get(field_name))
            if parsed is not None:
                candidates.append(parsed)
    if not candidates:
        return None
    return min(candidates)


def _resolve_metadata_timestamp(
    *,
    explicit: datetime | None,
    records: Sequence[Mapping[str, object]],
    fallback: datetime | None = None,
) -> datetime:
    """Resolve one deterministic timestamp for metadata sidecars."""
    if explicit is not None:
        return _normalize_metadata_timestamp(explicit)
    record_timestamp = _resolve_records_metadata_timestamp(records)
    if record_timestamp is not None:
        return record_timestamp
    if fallback is not None:
        return _normalize_metadata_timestamp(fallback)
    raise ValueError(
        "Deterministic metadata timestamp requires explicit time or record-level "
        "_lineage_created_at/_ingestion_ts anchors"
    )


def _build_silver_artifact_id(table_name: str, version_after: int | None) -> str:
    """Build canonical Silver artifact id."""
    provider_name, entity_name = _parse_table_name(table_name)
    dataset = DatasetRef(
        layer="silver",
        logical_name=f"{provider_name}.{entity_name}",
        version=version_after,
        provider=provider_name,
        entity=entity_name,
    )
    return str(dataset.node_id)


def _build_gold_artifact_id(table_name: str) -> str:
    """Build canonical Gold artifact id."""
    provider_name, entity_name = _parse_table_name(table_name)
    dataset = DatasetRef(
        layer="gold",
        logical_name=table_name,
        provider=provider_name,
        entity=entity_name,
    )
    return str(dataset.node_id)


class _MetadataBuilderBase:
    """Shared initialization for Silver/Gold metadata builders."""

    def __init__(
        self,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
    ) -> None:
        self._transform_version = transform_version
        self._transform_steps = transform_steps or ()

    def _build_composite_runtime_pipeline_lineage(
        self,
        *,
        table_name: str,
        now: datetime,
        run_id: str | None,
        sources_used: list[str] | None,
    ) -> tuple[RuntimeMetadata, PipelineMetadata, LineageMetadata]:
        """Build runtime/pipeline/lineage metadata for composite merged outputs."""
        from bioetl.domain.models.metadata import (
            LineageMetadata,
            PipelineMetadata,
            RuntimeMetadata,
            RunTypeEnum,
        )

        provider_name, entity_name = _parse_table_name(table_name)
        runtime = RuntimeMetadata(
            run_id=run_id or "",
            run_type=RunTypeEnum.INCREMENTAL,
            started_at_utc=now,
            completed_at_utc=now,
        )
        pipeline = PipelineMetadata(
            name=f"composite_{entity_name}",
            provider=provider_name,
            entity=entity_name,
            version=BIOETL_VERSION,
            git_commit=_get_git_commit_cached(),
        )
        lineage = LineageMetadata(
            bronze_paths=[],
            transform_version=self._transform_version or "1.0.0",
            transform_steps=(
                list(self._transform_steps) if self._transform_steps else ["merge"]
            ),
            source_tables=dict.fromkeys(sources_used or [], 0),
        )
        return runtime, pipeline, lineage

    @staticmethod
    def _build_merged_dq_summary(
        records: list[JsonDict],  # Any: heterogeneous metadata values
    ) -> DQSummary:
        """Build DQ summary for merged records."""
        from bioetl.domain.models.metadata import DQSummary

        total_records = len(records)
        dq_summary = DQSummary(
            total_records=len(records),
            valid_records=len(records),
            error_records=0,
            error_rate=0.0,
        )
        cv_summary = summarize_composite_cv_dq(records)
        if not cv_summary["has_signal"]:
            return dq_summary

        error_records = int(cv_summary["error_records"])
        warning_records = int(cv_summary["warning_records"])
        updated_summary: DQSummary = dq_summary.model_copy(
            update={
                "valid_records": max(total_records - error_records, 0),
                "error_records": error_records,
                "warning_records": warning_records,
                "error_rate": (error_records / total_records) if total_records else 0.0,
                "validation_passed": bool(cv_summary["validation_passed"]),
                "rule_provenance": cv_summary["rule_provenance"],
            }
        )
        return updated_summary

    @staticmethod
    def _build_environment_metadata() -> EnvironmentMetadata:
        """Build environment metadata for current process."""
        from bioetl.domain.models.metadata import EnvironmentMetadata

        return EnvironmentMetadata(
            hostname=hostname(),
            python_version=python_version(),
            bioetl_version=BIOETL_VERSION,
        )


__all__ = [
    "_MetadataBuilderBase",
    "_build_gold_artifact_id",
    "_build_silver_artifact_id",
    "_parse_table_name",
    "_resolve_metadata_timestamp",
    "_resolve_records_metadata_timestamp",
]
