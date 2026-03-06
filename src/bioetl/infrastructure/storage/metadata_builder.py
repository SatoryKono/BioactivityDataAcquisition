"""Metadata builder services for Medallion layer sidecar files.

Extracts metadata building logic from SilverWriter and GoldWriter
to reduce file size and improve maintainability.

Implements RULES.md §2.3 and ADR-026 for metadata creation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from platform import node as hostname
from platform import python_version
from typing import TYPE_CHECKING

from bioetl.domain.services.schema_metadata_extractor import extract_schema_metadata
from bioetl.domain.types import JsonDict
from bioetl.domain.version import get_version as _get_bioetl_version
from bioetl.infrastructure.storage.metadata_builder_composite_helpers import (
    build_composite_output_ext,
)

if TYPE_CHECKING:
    from bioetl.domain.medallion import GoldWriteMode
    from bioetl.domain.models.metadata import (
        BaseOutputMetadata,
        CompositeOutputExt,
        DQSummary,
        EnvironmentMetadata,
        GoldMetadata,
        GoldOutputExt,
        LineageMetadata,
        PipelineMetadata,
        RuntimeMetadata,
        SCDMetadata,
        SilverMetadata,
    )


def _get_git_commit_cached() -> str | None:
    """Get git commit hash directly via subprocess.

    This is a fallback for metadata builders when MetadataCoordinator
    is not available. Uses subprocess directly to avoid layer violations
    (infrastructure cannot import composition).

    Returns:
        Short git commit hash or None.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def _parse_table_name(table_name: str) -> tuple[str, str]:
    """Parse table name into provider and entity components.

    Handles multiple formats:
    - Dot notation: 'chembl.activity' -> ('chembl', 'activity')
    - Path notation: 'composite/publication' -> ('composite', 'publication')
    - Underscore notation: 'chembl_activity' -> ('chembl', 'activity')
    - Plain name: 'activity' -> ('unknown', 'activity')

    Args:
        table_name: Table name in any supported format.

    Returns:
        Tuple of (provider_name, entity_name).
    """
    if "." in table_name:
        parts = table_name.split(".")
        return parts[0], parts[1] if len(parts) > 1 else parts[0]
    elif "/" in table_name:
        parts = table_name.split("/")
        return (parts[0] if len(parts) > 1 else "composite"), parts[-1]
    elif "_" in table_name:
        parts = table_name.split("_", 1)
        return parts[0], parts[1] if len(parts) > 1 else parts[0]
    return "unknown", table_name if table_name else "unknown"


class _MetadataBuilderBase:
    """Shared initialization for Silver/Gold metadata builders."""

    def __init__(
        self,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
    ) -> None:
        """Initialize metadata builder.

        Args:
            transform_version: Semver version of transform (e.g., '1.0.0').
            transform_steps: Tuple of transform step names.
        """
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
            version=_get_bioetl_version(),
            git_commit=_get_git_commit_cached(),
        )
        lineage = LineageMetadata(
            bronze_paths=[],
            transform_version=self._transform_version or "1.0.0",
            transform_steps=list(self._transform_steps)
            if self._transform_steps
            else ["merge"],
            source_tables=dict.fromkeys(sources_used or [], 0),
        )
        return runtime, pipeline, lineage

    @staticmethod
    def _build_merged_dq_summary(
        records: list[JsonDict],  # Any: heterogeneous metadata values
    ) -> DQSummary:
        """Build DQ summary for merged records."""
        from bioetl.domain.models.metadata import DQSummary

        return DQSummary(
            total_records=len(records),
            valid_records=len(records),
            error_records=0,
            error_rate=0.0,
        )

    @staticmethod
    def _build_environment_metadata() -> EnvironmentMetadata:
        """Build environment metadata for current process."""
        from bioetl.domain.models.metadata import EnvironmentMetadata

        return EnvironmentMetadata(
            hostname=hostname(),
            python_version=python_version(),
            bioetl_version=_get_bioetl_version(),
        )


class SilverMetadataBuilder(_MetadataBuilderBase):
    """Builder for Silver layer metadata objects.

    Extracts the metadata building logic from SilverWriter to reduce
    file size and improve testability.

    Used for:
    - Standard Silver metadata (when MetadataCoordinator is not available)
    - Merged Silver metadata (for composite pipelines)
    """

    def build_merged_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[JsonDict],  # Any: heterogeneous metadata values
        primary_keys: list[str],
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        version_after: int | None = None,
        partition_by: list[str] | None = None,
    ) -> SilverMetadata:
        """Build Silver metadata for merged composite data."""
        from bioetl.domain.models.metadata import (
            BaseOutputMetadata,
            DeltaMetrics,
            SilverMetadata,
            SilverOutputExt,
        )

        now = datetime.now(UTC)
        runtime, pipeline, lineage = self._build_composite_runtime_pipeline_lineage(
            table_name=table_name,
            now=now,
            run_id=run_id,
            sources_used=sources_used,
        )
        delta = DeltaMetrics(
            table_path=table_path,
            operation="overwrite",
            primary_key=primary_keys,
            partition_by=partition_by or [],
            version_after=version_after,
            rows_inserted=len(records),
        )
        dq_summary = self._build_merged_dq_summary(records)
        output = BaseOutputMetadata(
            record_count=len(records),
            write_started_at=now,
            write_completed_at=now,
        )
        output_ext = SilverOutputExt(delta_version_after=version_after)
        return SilverMetadata(
            runtime=runtime,
            pipeline=pipeline,
            lineage=lineage,
            delta=delta,
            dq_summary=dq_summary,
            output=output,
            output_ext=output_ext,
            environment=self._build_environment_metadata(),
        )


class GoldMetadataBuilder(_MetadataBuilderBase):
    """Builder for Gold layer metadata objects.

    Extracts the metadata building logic from GoldWriter to reduce
    file size and improve testability.

    Used for:
    - Standard Gold metadata (when MetadataCoordinator is not available)
    - Merged Gold metadata (for composite pipelines)
    """

    def _build_fallback_runtime_and_pipeline(
        self,
        *,
        table_name: str,
        now: datetime,
        run_id: object | None,
    ) -> tuple[RuntimeMetadata, PipelineMetadata]:
        """Build runtime and pipeline metadata for fallback mode."""
        from bioetl.domain.models.metadata import (
            PipelineMetadata,
            RuntimeMetadata,
            RunTypeEnum,
        )

        provider_name, entity_name = _parse_table_name(table_name)
        runtime = RuntimeMetadata(
            run_id=str(run_id) if run_id else "",
            run_type=RunTypeEnum.INCREMENTAL,
            started_at_utc=now,
            completed_at_utc=now,
        )
        pipeline = PipelineMetadata(
            name=f"{provider_name}_{entity_name}",
            provider=provider_name,
            entity=entity_name,
            version=_get_bioetl_version(),
            git_commit=_get_git_commit_cached(),
        )
        return runtime, pipeline

    def _build_fallback_dq_and_output(
        self,
        *,
        records: list[JsonDict],  # Any: heterogeneous metadata values
        now: datetime,
    ) -> tuple[DQSummary, BaseOutputMetadata, GoldOutputExt | CompositeOutputExt]:
        """Build DQ summary and unified output structures for fallback mode."""
        from bioetl.domain.models.metadata import (
            BaseOutputMetadata,
            DQSummary,
            GoldOutputExt,
        )

        dq_summary = DQSummary(
            total_records=len(records),
            valid_records=len(records),
        )
        composite_ext = build_composite_output_ext(records)
        output = BaseOutputMetadata(
            record_count=len(records),
            write_started_at=now,
            write_completed_at=now,
            composite_run_id=composite_ext.composite_run_id if composite_ext else None,
        )
        output_ext = composite_ext or GoldOutputExt()
        return dq_summary, output, output_ext

    def _build_fallback_scd_metadata(
        self,
        *,
        mode: GoldWriteMode,
        scd_config: JsonDict | None,  # Any: dynamic layer config
    ) -> SCDMetadata | None:
        """Build SCD metadata only for SCD2 mode with config present."""
        from bioetl.domain.medallion import GoldWriteMode
        from bioetl.domain.models.metadata import SCDMetadata

        if mode != GoldWriteMode.SCD2 or not scd_config:
            return None
        return SCDMetadata(
            enabled=True,
            effective_date_column=scd_config.get("valid_from_col", "_valid_from"),
            end_date_column=scd_config.get("valid_to_col", "_valid_to"),
            current_flag_column=scd_config.get("current_flag_col", "_is_current"),
        )

    def build_fallback_metadata(
        self,
        table_name: str,
        records: list[JsonDict],  # Any: heterogeneous metadata values
        mode: GoldWriteMode,
        scd_config: JsonDict | None = None,  # Any: dynamic layer config
        ingestion_ts: datetime | None = None,
        run_id: object | None = None,
        gold_schema: object | None = None,
    ) -> GoldMetadata:
        """Build Gold metadata using fallback logic (no coordinator)."""
        from bioetl.domain.models.metadata import (
            GoldMetadata,
            LineageMetadata,
        )

        now = ingestion_ts or datetime.now(UTC)
        runtime, pipeline = self._build_fallback_runtime_and_pipeline(
            table_name=table_name,
            now=now,
            run_id=run_id,
        )
        lineage = LineageMetadata()
        dq_summary, output, output_ext = self._build_fallback_dq_and_output(
            records=records,
            now=now,
        )
        scd = self._build_fallback_scd_metadata(mode=mode, scd_config=scd_config)
        schema_info = extract_schema_metadata(gold_schema)
        environment = self._build_environment_metadata()

        return GoldMetadata(
            runtime=runtime,
            pipeline=pipeline,
            lineage=lineage,
            schema=schema_info,
            dq_summary=dq_summary,
            output=output,
            output_ext=output_ext,
            scd=scd,
            environment=environment,
        )

    @staticmethod
    def _build_merged_output(
        *,
        records: list[JsonDict],  # Any: heterogeneous metadata values
        now: datetime,
    ) -> tuple[BaseOutputMetadata, GoldOutputExt | CompositeOutputExt]:
        """Build unified output metadata for merged Gold records."""
        from bioetl.domain.models.metadata import BaseOutputMetadata, GoldOutputExt

        composite_ext = build_composite_output_ext(records)
        output = BaseOutputMetadata(
            record_count=len(records),
            write_started_at=now,
            write_completed_at=now,
            composite_run_id=composite_ext.composite_run_id if composite_ext else None,
        )
        return output, composite_ext or GoldOutputExt()

    def build_merged_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[JsonDict],  # Any: heterogeneous metadata values
        primary_keys: list[str],
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        gold_schema: object | None = None,
    ) -> GoldMetadata:
        """Build Gold metadata for merged composite data."""
        from bioetl.domain.models.metadata import (
            GoldMetadata,
        )

        now = datetime.now(UTC)
        runtime, pipeline, lineage = self._build_composite_runtime_pipeline_lineage(
            table_name=table_name,
            now=now,
            run_id=run_id,
            sources_used=sources_used,
        )
        dq_summary = self._build_merged_dq_summary(records)
        output, output_ext = self._build_merged_output(
            records=records,
            now=now,
        )
        schema_info = extract_schema_metadata(gold_schema)

        return GoldMetadata(
            runtime=runtime,
            pipeline=pipeline,
            lineage=lineage,
            schema=schema_info,
            dq_summary=dq_summary,
            output=output,
            output_ext=output_ext,
            environment=self._build_environment_metadata(),
        )


__all__ = [
    "GoldMetadataBuilder",
    "SilverMetadataBuilder",
]
