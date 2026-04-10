"""Metadata builder services for Medallion layer sidecar files.

Extracts metadata building logic from SilverWriter and GoldWriter
to reduce file size and improve maintainability.

Implements RULES.md §2.3 and ADR-026 for metadata creation.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl import __version__ as BIOETL_VERSION
from bioetl.domain.services.composite_metadata_helpers import (
    extract_composite_output_ext as _extract_composite_output_ext,
)
from bioetl.domain.services.schema_metadata_extractor import extract_schema_metadata
from bioetl.domain.types import JsonDict, ScdConfig
from bioetl.infrastructure.storage.metadata.builder_base import (
    _build_gold_artifact_id,
    _build_silver_artifact_id,
    _get_git_commit_cached,
    _MetadataBuilderBase,
    _parse_table_name,
    _resolve_metadata_timestamp,
)

if TYPE_CHECKING:
    from bioetl.domain.medallion import GoldWriteMode
    from bioetl.domain.models.metadata import (
        BaseOutputMetadata,
        CompositeOutputExt,
        DQSummary,
        GoldMetadata,
        GoldOutputExt,
        LineageMetadata,
        PipelineMetadata,
        RuntimeMetadata,
        SCDMetadata,
        SilverMetadata,
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
        completed_at: datetime | None = None,
    ) -> SilverMetadata:
        """Build Silver metadata for merged composite data.

        Returns:
            SilverMetadata instance populated with composite runtime, pipeline, lineage, and DQ info.
        """
        from bioetl.domain.models.metadata import (
            BaseOutputMetadata,
            DeltaMetrics,
            SilverMetadata,
            SilverOutputExt,
        )

        now = _resolve_metadata_timestamp(
            explicit=completed_at,
            records=records,
        )
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
            artifact_id=_build_silver_artifact_id(table_name, version_after),
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
        """Build runtime and pipeline metadata for fallback mode.

        Returns:
            Tuple of (RuntimeMetadata, PipelineMetadata) built from parsed table name components.
        """
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
            version=BIOETL_VERSION,
            git_commit=_get_git_commit_cached(),
        )
        return runtime, pipeline

    def _build_fallback_dq_and_output(
        self,
        *,
        records: list[JsonDict],  # Any: heterogeneous metadata values
        now: datetime,
        artifact_id: str,
    ) -> tuple[DQSummary, BaseOutputMetadata, GoldOutputExt | CompositeOutputExt]:
        """Build DQ summary and unified output structures for fallback mode.

        Returns:
            Tuple of (DQSummary, BaseOutputMetadata, GoldOutputExt or CompositeOutputExt).
        """
        from bioetl.domain.models.metadata import (
            DQSummary,
        )

        dq_summary = DQSummary(
            total_records=len(records),
            valid_records=len(records),
        )
        output, output_ext = self._build_output_with_composite_ext(
            records=records,
            now=now,
        )
        output.artifact_id = artifact_id
        return dq_summary, output, output_ext

    def _build_fallback_lineage(
        self,
        *,
        silver_refs: list[object] | None,
    ) -> "LineageMetadata":
        """Build deterministic fallback lineage metadata."""
        from bioetl.domain.models.metadata import LineageMetadata

        source_tables: dict[str, int] = {}
        for ref in silver_refs or []:
            table_name = getattr(ref, "table_name", None)
            delta_version = getattr(ref, "delta_version", None)
            if isinstance(table_name, str) and isinstance(delta_version, int):
                source_tables[table_name] = delta_version

        return LineageMetadata(
            transform_version=self._transform_version or "1.0.0",
            transform_steps=list(self._transform_steps),
            source_tables=source_tables,
        )

    def _build_fallback_scd_metadata(
        self,
        *,
        mode: GoldWriteMode,
        scd_config: ScdConfig | None,
    ) -> SCDMetadata | None:
        """Build SCD metadata only for SCD2 mode with config present.

        Returns:
            SCDMetadata instance if mode is SCD2 and config is provided, None otherwise.
        """
        from bioetl.domain.medallion import GoldWriteMode
        from bioetl.domain.models.metadata import SCDMetadata

        normalized_scd_config = (
            ScdConfig.from_mapping(scd_config)
            if isinstance(scd_config, Mapping)
            else scd_config
        )

        if mode != GoldWriteMode.SCD2 or not normalized_scd_config:
            return None
        return SCDMetadata(
            enabled=True,
            effective_date_column=normalized_scd_config.valid_from_col,
            end_date_column=normalized_scd_config.valid_to_col,
            current_flag_column=normalized_scd_config.current_flag_col,
        )

    def build_fallback_metadata(
        self,
        table_name: str,
        records: list[JsonDict],  # Any: heterogeneous metadata values
        mode: GoldWriteMode,
        scd_config: ScdConfig | None = None,
        ingestion_ts: datetime | None = None,
        run_id: object | None = None,
        silver_refs: list[object] | None = None,
        gold_schema: object | None = None,
    ) -> GoldMetadata:
        """Build Gold metadata using fallback logic (no coordinator).

        Returns:
            GoldMetadata instance with runtime, pipeline, DQ, SCD, and environment info.
        """
        from bioetl.domain.models.metadata import GoldMetadata

        now = _resolve_metadata_timestamp(
            explicit=ingestion_ts,
            records=records,
        )
        runtime, pipeline = self._build_fallback_runtime_and_pipeline(
            table_name=table_name,
            now=now,
            run_id=run_id,
        )
        lineage = self._build_fallback_lineage(silver_refs=silver_refs)
        dq_summary, output, output_ext = self._build_fallback_dq_and_output(
            records=records,
            now=now,
            artifact_id=_build_gold_artifact_id(table_name),
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
    def _build_output_with_composite_ext(
        *,
        records: list[JsonDict],  # Any: heterogeneous metadata values
        now: datetime,
    ) -> tuple[BaseOutputMetadata, GoldOutputExt | CompositeOutputExt]:
        """Build output metadata and optional composite extension.

        Returns:
            Tuple of (BaseOutputMetadata, GoldOutputExt or CompositeOutputExt).
        """
        from bioetl.domain.models.metadata import BaseOutputMetadata, GoldOutputExt

        composite_ext = _extract_composite_output_ext(records)
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
        completed_at: datetime | None = None,
    ) -> GoldMetadata:
        """Build Gold metadata for merged composite data.

        Returns:
            GoldMetadata instance populated with composite runtime, pipeline, lineage, and schema info.
        """
        from bioetl.domain.models.metadata import (
            GoldMetadata,
        )

        now = _resolve_metadata_timestamp(
            explicit=completed_at,
            records=records,
        )
        runtime, pipeline, lineage = self._build_composite_runtime_pipeline_lineage(
            table_name=table_name,
            now=now,
            run_id=run_id,
            sources_used=sources_used,
        )
        dq_summary = self._build_merged_dq_summary(records)
        output, output_ext = self._build_output_with_composite_ext(
            records=records,
            now=now,
        )
        output.artifact_id = _build_gold_artifact_id(table_name)
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
    "_parse_table_name",
]
