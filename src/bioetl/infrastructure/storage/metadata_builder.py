"""Metadata builder services for Medallion layer sidecar files.

Extracts metadata building logic from SilverWriter and GoldWriter
to reduce file size and improve maintainability.

Implements RULES.md §2.3 and ADR-026 for metadata creation.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from platform import node as hostname
from platform import python_version
from typing import TYPE_CHECKING, Any, Literal

from bioetl.domain.version import get_version as _get_bioetl_version

if TYPE_CHECKING:
    from bioetl.domain.medallion import GoldWriteMode
    from bioetl.domain.models.metadata import (
        GoldMetadata,
        SchemaMetadata,
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


def _extract_schema_metadata(gold_schema: Any | None) -> SchemaMetadata:
    """Extract schema metadata from a Pandera DataFrameModel.

    Extracts contract_path, version, columns, and validation mode from
    the Pandera schema class for Gold layer metadata tracking.

    Args:
        gold_schema: Pandera DataFrameModel class (not instance).

    Returns:
        SchemaMetadata with populated fields, or default if schema is None.
    """
    from bioetl.domain.models.metadata import SchemaColumnMetadata, SchemaMetadata

    if gold_schema is None:
        return SchemaMetadata()

    # Extract contract_path from module path
    contract_path: str | None = None
    try:
        module = inspect.getmodule(gold_schema)
        if module and module.__file__:
            # Convert absolute path to relative path from project root
            # e.g., .../src/bioetl/domain/contracts/gold/chembl.py
            # -> src/bioetl/domain/contracts/gold/chembl.py
            file_path = module.__file__
            if "src/bioetl" in file_path:
                idx = file_path.find("src/bioetl")
                contract_path = file_path[idx:]
    except (AttributeError, OSError, TypeError):
        contract_path = None

    # Extract schema version from Config if defined
    version = "1.0"
    if hasattr(gold_schema, "Config"):
        config = gold_schema.Config
        version = getattr(config, "version", "1.0")
        if not isinstance(version, str):
            version = str(version)

    # Determine validation mode
    validation: Literal["strict", "lenient"] = "strict"
    if hasattr(gold_schema, "Config"):
        config = gold_schema.Config
        is_strict = getattr(config, "strict", True)
        validation = "strict" if is_strict else "lenient"

    # Extract column definitions
    columns: list[SchemaColumnMetadata] = []
    try:
        # Try to get schema columns using Pandera's to_schema() method
        if hasattr(gold_schema, "to_schema"):
            schema_instance = gold_schema.to_schema()
            if hasattr(schema_instance, "columns"):
                for col_name, col_schema in schema_instance.columns.items():
                    # Get the dtype as string
                    dtype_str = str(col_schema.dtype) if col_schema.dtype else "object"
                    # Simplify dtype string (remove pandera.dtypes. prefix)
                    if "." in dtype_str:
                        dtype_str = dtype_str.split(".")[-1]

                    nullable = getattr(col_schema, "nullable", True)
                    columns.append(
                        SchemaColumnMetadata(
                            name=col_name,
                            type=dtype_str,
                            nullable=nullable,
                        )
                    )
    except (AttributeError, TypeError, ValueError):
        # If schema extraction fails, leave columns empty
        columns = []

    return SchemaMetadata(
        contract_path=contract_path,
        version=version,
        validation=validation,
        columns=columns,
    )


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
            BaseOutputMetadata,
            DeltaMetrics,
            DQSummary,
            EnvironmentMetadata,
            LineageMetadata,
            PipelineMetadata,
            RuntimeMetadata,
            RunTypeEnum,
            SilverMetadata,
            SilverOutputExt,
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

        # Use unified output structure (ADR-029)
        output = BaseOutputMetadata(
            record_count=len(records),
            write_started_at=now,
            write_completed_at=now,
        )

        output_ext = SilverOutputExt(
            delta_version_after=version_after,
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
            output_ext=output_ext,
            environment=environment,
        )


class GoldMetadataBuilder(_MetadataBuilderBase):
    """Builder for Gold layer metadata objects.

    Extracts the metadata building logic from GoldWriter to reduce
    file size and improve testability.

    Used for:
    - Standard Gold metadata (when MetadataCoordinator is not available)
    - Merged Gold metadata (for composite pipelines)
    """

    def build_fallback_metadata(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        mode: GoldWriteMode,
        scd_config: dict[str, Any] | None = None,
        ingestion_ts: datetime | None = None,
        run_id: Any | None = None,
        gold_schema: Any | None = None,
    ) -> GoldMetadata:
        """Build Gold metadata using fallback logic (no coordinator).

        Args:
            table_name: Table name for pipeline identification.
            records: List of records written.
            mode: Gold write mode (overwrite, append, scd2).
            scd_config: SCD2 configuration if applicable.
            ingestion_ts: Ingestion timestamp.
            run_id: Run identifier.
            gold_schema: Optional Pandera schema class for extracting schema metadata.

        Returns:
            GoldMetadata object ready for serialization.
        """
        from bioetl.domain.medallion import GoldWriteMode
        from bioetl.domain.models.metadata import (
            BaseOutputMetadata,
            DQSummary,
            EnvironmentMetadata,
            GoldMetadata,
            GoldOutputExt,
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
            version=_get_bioetl_version(),
            git_commit=_get_git_commit_cached(),
        )

        lineage = LineageMetadata()

        dq_summary = DQSummary(
            total_records=len(records),
            valid_records=len(records),
        )

        # Use unified output structure (ADR-029)
        output = BaseOutputMetadata(
            record_count=len(records),
            write_started_at=now,
            write_completed_at=now,
        )

        output_ext = GoldOutputExt()

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

        # Extract schema metadata from Gold schema
        schema_info = _extract_schema_metadata(gold_schema)

        # Note: schema_info uses Field(alias="schema") with populate_by_name=True
        # mypy doesn't understand this Pydantic feature, but it works at runtime
        return GoldMetadata(  # type: ignore[call-arg]
            runtime=runtime,
            pipeline=pipeline,
            lineage=lineage,
            schema_info=schema_info,
            dq_summary=dq_summary,
            output=output,
            output_ext=output_ext,
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
        gold_schema: Any | None = None,
    ) -> GoldMetadata:
        """Build Gold metadata for merged composite data.

        Args:
            table_path: Full path to the Delta table.
            table_name: Table name for pipeline identification.
            records: List of records written.
            primary_keys: Primary key columns (unused but kept for symmetry).
            run_id: Composite run ID.
            sources_used: List of source pipelines.
            gold_schema: Optional Pandera schema class for extracting schema metadata.

        Returns:
            GoldMetadata object ready for serialization.
        """
        from bioetl.domain.models.metadata import (
            BaseOutputMetadata,
            DQSummary,
            EnvironmentMetadata,
            GoldMetadata,
            GoldOutputExt,
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

        dq_summary = DQSummary(
            total_records=len(records),
            valid_records=len(records),
            error_records=0,
            error_rate=0.0,
        )

        # Use unified output structure (ADR-029)
        output = BaseOutputMetadata(
            record_count=len(records),
            write_started_at=now,
            write_completed_at=now,
        )

        output_ext = GoldOutputExt()

        environment = EnvironmentMetadata(
            hostname=hostname(),
            python_version=python_version(),
            bioetl_version=_get_bioetl_version(),
        )

        # Extract schema metadata from Gold schema
        schema_info = _extract_schema_metadata(gold_schema)

        # Note: schema_info uses Field(alias="schema") with populate_by_name=True
        return GoldMetadata(  # type: ignore[call-arg]
            runtime=runtime,
            pipeline=pipeline,
            lineage=lineage,
            schema_info=schema_info,
            dq_summary=dq_summary,
            output=output,
            output_ext=output_ext,
            environment=environment,
        )


__all__ = [
    "GoldMetadataBuilder",
    "SilverMetadataBuilder",
]
