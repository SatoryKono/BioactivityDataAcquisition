"""Metadata builder services for Medallion layer sidecar files.

Extracts metadata building logic from SilverWriter and GoldWriter
to reduce file size and improve maintainability.

Implements RULES.md §2.3 and ADR-026 for metadata creation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from importlib.metadata import version as pkg_version
from platform import node as hostname
from platform import python_version
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.medallion import GoldWriteMode
    from bioetl.domain.models.metadata import GoldMetadata, SilverMetadata


def _get_bioetl_version() -> str:
    """Get bioetl package version.

    Returns:
        Version string or 'unknown' if not installed.
    """
    try:
        return pkg_version("bioetl")
    except Exception:
        return "unknown"


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


class SilverMetadataBuilder:
    """Builder for Silver layer metadata objects.

    Extracts the metadata building logic from SilverWriter to reduce
    file size and improve testability.

    Used for:
    - Standard Silver metadata (when MetadataCoordinator is not available)
    - Merged Silver metadata (for composite pipelines)
    """

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

    def build_merged_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        version_after: int | None = None,
        partition_by: list[str] | None = None,
    ) -> SilverMetadata:
        """Build Silver metadata for merged composite data.

        Args:
            table_path: Full path to the Delta table.
            table_name: Table name for pipeline identification.
            records: List of records written.
            primary_keys: Primary key columns used.
            run_id: Composite run ID.
            sources_used: List of source pipelines (e.g., ['seed', 'crossref']).
            version_after: Delta table version after write.
            partition_by: Partition columns used for the Delta table.

        Returns:
            SilverMetadata object ready for serialization.
        """
        from bioetl.domain.models.metadata import (
            DeltaMetrics,
            DQSummary,
            EnvironmentMetadata,
            LineageMetadata,
            PipelineMetadata,
            RuntimeMetadata,
            RunTypeEnum,
            SilverMetadata,
            SilverOutputMetadata,
        )

        provider_name, entity_name = _parse_table_name(table_name)

        now = datetime.now(UTC)
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
        )

        lineage = LineageMetadata(
            bronze_paths=[],
            transform_version=self._transform_version or "1.0.0",
            transform_steps=list(self._transform_steps)
            if self._transform_steps
            else ["merge"],
            source_tables=dict.fromkeys(sources_used or [], 0),
        )

        delta = DeltaMetrics(
            table_path=table_path,
            operation="overwrite",
            primary_key=primary_keys,
            partition_by=partition_by or [],
            version_after=version_after,
            rows_inserted=len(records),
        )

        dq_summary = DQSummary(
            total_records=len(records),
            valid_records=len(records),
            error_records=0,
            error_rate=0.0,
        )

        output = SilverOutputMetadata(
            record_count=len(records),
        )

        environment = EnvironmentMetadata(
            hostname=hostname(),
            python_version=python_version(),
            bioetl_version=_get_bioetl_version(),
        )

        return SilverMetadata(
            runtime=runtime,
            pipeline=pipeline,
            lineage=lineage,
            delta=delta,
            dq_summary=dq_summary,
            output=output,
            environment=environment,
        )


class GoldMetadataBuilder:
    """Builder for Gold layer metadata objects.

    Extracts the metadata building logic from GoldWriter to reduce
    file size and improve testability.

    Used for:
    - Standard Gold metadata (when MetadataCoordinator is not available)
    - Merged Gold metadata (for composite pipelines)
    """

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

    def build_fallback_metadata(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        mode: GoldWriteMode,
        scd_config: dict[str, Any] | None = None,
        ingestion_ts: datetime | None = None,
        run_id: Any | None = None,
    ) -> GoldMetadata:
        """Build Gold metadata using fallback logic (no coordinator).

        Args:
            table_name: Table name for pipeline identification.
            records: List of records written.
            mode: Gold write mode (overwrite, append, scd2).
            scd_config: SCD2 configuration if applicable.
            ingestion_ts: Ingestion timestamp.
            run_id: Run identifier.

        Returns:
            GoldMetadata object ready for serialization.
        """
        from bioetl.domain.medallion import GoldWriteMode
        from bioetl.domain.models.metadata import (
            DQSummary,
            EnvironmentMetadata,
            GoldMetadata,
            GoldOutputMetadata,
            LineageMetadata,
            PipelineMetadata,
            RuntimeMetadata,
            RunTypeEnum,
            SCDMetadata,
        )

        provider_name, entity_name = _parse_table_name(table_name)

        now = ingestion_ts or datetime.now(UTC)
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
        )

        lineage = LineageMetadata()

        dq_summary = DQSummary(
            total_records=len(records),
            valid_records=len(records),
        )

        output = GoldOutputMetadata(
            record_count=len(records),
        )

        scd = None
        if mode == GoldWriteMode.SCD2 and scd_config:
            scd = SCDMetadata(
                enabled=True,
                effective_date_column=scd_config.get("valid_from_col", "_valid_from"),
                end_date_column=scd_config.get("valid_to_col", "_valid_to"),
                current_flag_column=scd_config.get("current_flag_col", "_is_current"),
            )

        environment = EnvironmentMetadata(
            hostname=hostname(),
            python_version=python_version(),
            bioetl_version=_get_bioetl_version(),
        )

        return GoldMetadata(
            runtime=runtime,
            pipeline=pipeline,
            lineage=lineage,
            dq_summary=dq_summary,
            output=output,
            scd=scd,
            environment=environment,
        )

    def build_merged_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> GoldMetadata:
        """Build Gold metadata for merged composite data.

        Args:
            table_path: Full path to the Delta table.
            table_name: Table name for pipeline identification.
            records: List of records written.
            primary_keys: Primary key columns (unused but kept for symmetry).
            run_id: Composite run ID.
            sources_used: List of source pipelines.

        Returns:
            GoldMetadata object ready for serialization.
        """
        from bioetl.domain.models.metadata import (
            DQSummary,
            EnvironmentMetadata,
            GoldMetadata,
            GoldOutputMetadata,
            LineageMetadata,
            PipelineMetadata,
            RuntimeMetadata,
            RunTypeEnum,
        )

        provider_name, entity_name = _parse_table_name(table_name)

        now = datetime.now(UTC)
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
        )

        lineage = LineageMetadata(
            bronze_paths=[],
            transform_version=self._transform_version or "1.0.0",
            transform_steps=list(self._transform_steps)
            if self._transform_steps
            else ["merge"],
            source_tables=dict.fromkeys(sources_used or [], 0),
        )

        dq_summary = DQSummary(
            total_records=len(records),
            valid_records=len(records),
            error_records=0,
            error_rate=0.0,
        )

        output = GoldOutputMetadata(
            record_count=len(records),
        )

        environment = EnvironmentMetadata(
            hostname=hostname(),
            python_version=python_version(),
            bioetl_version=_get_bioetl_version(),
        )

        return GoldMetadata(
            runtime=runtime,
            pipeline=pipeline,
            lineage=lineage,
            dq_summary=dq_summary,
            output=output,
            environment=environment,
        )


__all__ = [
    "GoldMetadataBuilder",
    "SilverMetadataBuilder",
]
