"""Assembly helpers for Silver/Gold metadata sidecar models."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services.lineage.metadata_assemblers_helpers import (
    PipelineMetadataBuilderProtocol,
    RuntimeMetadataBuilderProtocol,
    _build_dataset_content_hash,
    _build_gold_dq_summary,
    _build_gold_lineage,
    _build_gold_output,
    _build_gold_scd,
    _build_runtime_duration,
    _build_silver_artifact_id,
    _build_silver_delta,
    _build_silver_dq_summary,
    _build_silver_lineage,
    _extract_composite_output_ext,
    _resolve_bronze_paths,
    _resolve_gold_source_tables,
    _resolve_record_count,
    _resolve_source_batch_ids,
    _resolve_transform_metadata,
)
from bioetl.domain.behavior.schema_metadata_extractor import extract_schema_metadata
from bioetl.domain.models.metadata import (
    BaseOutputMetadata,
    EnvironmentMetadata,
    GoldMetadata,
    GoldOutputExt,
    SilverMetadata,
    SilverOutputExt,
)
from bioetl.domain.ports import GoldMetadataInput, SilverMetadataInput
from bioetl.domain.value_objects.run_context import RunContext


@dataclass(slots=True, frozen=True)
class SilverMetadataService:
    """Assemble Silver metadata from inputs and injected metadata builders."""

    run_context: RunContext
    runtime_metadata_builder: RuntimeMetadataBuilderProtocol
    pipeline_metadata_builder: PipelineMetadataBuilderProtocol
    environment_metadata: EnvironmentMetadata

    def assemble(self, input_data: SilverMetadataInput) -> SilverMetadata:
        """Build complete Silver metadata payload.

        Args:
            input_data: SilverMetadataInput with records, lineage sources, timing,
                and DQ summary data needed to assemble the metadata sidecar.

        Returns:
            SilverMetadata assembled from the provided input and service context.

        Raises:
            ValueError: If records is empty and total_records is None.
        """
        if not input_data.records and input_data.total_records is None:
            raise ValueError("Cannot create Silver metadata without records")

        source_batch_ids = _resolve_source_batch_ids(input_data)
        bronze_paths = _resolve_bronze_paths(input_data)
        transform_version, transform_steps = _resolve_transform_metadata(
            run_context=self.run_context,
            transform_version=input_data.transform_version,
            transform_steps=input_data.transform_steps,
        )
        lineage = _build_silver_lineage(
            source_batch_ids=source_batch_ids,
            bronze_paths=bronze_paths,
            transform_version=transform_version,
            transform_steps=transform_steps,
        )

        record_count = _resolve_record_count(
            records=input_data.records,
            total_records=input_data.total_records,
        )
        delta = _build_silver_delta(input_data=input_data, rows_inserted=record_count)
        dq_summary = _build_silver_dq_summary(
            input_data=input_data,
            record_count=record_count,
            run_context=self.run_context,
        )
        duration_seconds = _build_runtime_duration(
            input_data.started_at, input_data.completed_at
        )

        output = BaseOutputMetadata(
            artifact_id=_build_silver_artifact_id(
                run_context=self.run_context,
                input_data=input_data,
            ),
            record_count=record_count,
            total_bytes=input_data.total_bytes,
            content_hash=_build_dataset_content_hash(
                provider=self.run_context.provider,
                records=input_data.records,
            ),
            write_started_at=input_data.started_at,
            write_completed_at=input_data.completed_at,
        )
        output_ext = SilverOutputExt(
            delta_version_before=input_data.version_before,
            delta_version_after=input_data.version_after,
        )

        return SilverMetadata(
            runtime=self.runtime_metadata_builder(
                started_at=input_data.started_at,
                completed_at=input_data.completed_at,
                duration_seconds=duration_seconds,
            ),
            pipeline=self.pipeline_metadata_builder(),
            lineage=lineage,
            delta=delta,
            dq_summary=dq_summary,
            output=output,
            output_ext=output_ext,
            environment=self.environment_metadata,
            dq_report_path=input_data.dq_report_path,
            governance=input_data.governance,
        )


@dataclass(slots=True, frozen=True)
class GoldMetadataService:
    """Assemble Gold metadata from inputs and injected metadata builders."""

    run_context: RunContext
    runtime_metadata_builder: RuntimeMetadataBuilderProtocol
    pipeline_metadata_builder: PipelineMetadataBuilderProtocol
    environment_metadata: EnvironmentMetadata

    def assemble(self, input_data: GoldMetadataInput) -> GoldMetadata:
        """Build complete Gold metadata payload.

        Args:
            input_data: GoldMetadataInput with records, schema, lineage sources,
                partition info, and SCD data needed to assemble the metadata sidecar.

        Returns:
            GoldMetadata assembled from the provided input and service context.

        Raises:
            ValueError: If records is empty and total_records is None.
        """
        if not input_data.records and input_data.total_records is None:
            raise ValueError("Cannot create Gold metadata without records")

        source_tables = _resolve_gold_source_tables(input_data)
        transform_version, transform_steps = _resolve_transform_metadata(
            run_context=self.run_context,
            transform_version=input_data.transform_version,
            transform_steps=input_data.transform_steps,
        )
        lineage = _build_gold_lineage(
            source_tables=source_tables,
            transform_version=transform_version,
            transform_steps=transform_steps,
        )

        record_count = _resolve_record_count(
            records=input_data.records,
            total_records=input_data.total_records,
        )
        dq_summary = _build_gold_dq_summary(
            input_data=input_data,
            record_count=record_count,
            run_context=self.run_context,
        )

        records = input_data.records or []
        composite_ext = _extract_composite_output_ext(
            records=records,
            partition_count=input_data.partition_count,
            schema_validation_enabled=input_data.schema_validation_enabled,
            schema_validation_strict=input_data.schema_validation_strict,
            composite_run_id=input_data.composite_run_id,
            lineage_created_at=input_data.lineage_created_at,
        )
        output = _build_gold_output(
            run_context=self.run_context,
            input_data=input_data,
            record_count=record_count,
            composite_ext=composite_ext,
        )
        output_ext = composite_ext or GoldOutputExt(
            partition_count=input_data.partition_count
        )
        scd = _build_gold_scd(input_data)

        schema_info = extract_schema_metadata(input_data.schema_inspection)
        return GoldMetadata(
            runtime=self.runtime_metadata_builder(
                completed_at=input_data.completed_at,
                duration_seconds=0.0,
            ),
            pipeline=self.pipeline_metadata_builder(),
            lineage=lineage,
            schema=schema_info,
            dq_summary=dq_summary,
            output=output,
            output_ext=output_ext,
            scd=scd,
            environment=self.environment_metadata,
            dq_report_path=input_data.dq_report_path,
            governance=input_data.governance,
        )


__all__ = [
    "GoldMetadataService",
    "PipelineMetadataBuilderProtocol",
    "RuntimeMetadataBuilderProtocol",
    "SilverMetadataService",
]
