"""Centralized Metadata Coordinator Service.

Provides a single source of truth for creating metadata across all Medallion layers.
Eliminates duplication of RuntimeMetadata, PipelineMetadata, and EnvironmentMetadata
creation logic that was previously scattered across Bronze, Silver, and Gold writers.

Implements:
- Consistent run_id and timestamps across layers
- Cached environment metadata (computed once)
- Factory methods for layer-specific metadata
- Implements MetadataCoordinatorPort from domain.ports

Architecture:
- Composition Service (not Infrastructure)
- Accepts RunContext once at initialization
- Pure Python, no I/O operations
"""

from __future__ import annotations

import inspect
import platform
import socket
from datetime import datetime
from functools import cached_property
from typing import Any, Literal

from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.domain.models.metadata import (
    BronzeMetadata,
    DeltaMetrics,
    DQSummary,
    EnvironmentMetadata,
    FileOutputMetadata,
    GoldMetadata,
    GoldOutputMetadata,
    LineageMetadata,
    OutputMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    RunTypeEnum,
    SCDMetadata,
    SchemaColumnMetadata,
    SchemaMetadata,
    SilverMetadata,
    SilverOutputMetadata,
    SourceMetadata,
)
from bioetl.domain.ports import (
    BronzeMetadataInput,
    GoldMetadataInput,
    SilverMetadataInput,
)
from bioetl.domain.types import RunType
from bioetl.domain.value_objects.run_context import RunContext


def _get_bioetl_version() -> str:
    """Get BioETL package version.

    Returns:
        Package version string.

    Raises:
        PackageNotFoundError: If bioetl package is not installed.
    """
    from importlib.metadata import version as pkg_version

    return pkg_version("bioetl")


class MetadataCoordinator:
    """Centralized coordinator for metadata creation across Medallion layers.

    Creates consistent metadata with shared run_id, timestamps, and pipeline
    identification. Environment metadata is computed once and cached.

    Example:
        >>> from datetime import UTC, datetime
        >>> from uuid import uuid4
        >>> context = RunContext.create(
        ...     run_id=RunID(uuid4()),
        ...     run_type=RunType.INCREMENTAL,
        ...     started_at=datetime.now(UTC),
        ...     provider="chembl",
        ...     entity="activity",
        ... )
        >>> coordinator = MetadataCoordinator(context)
        >>> bronze_input = BronzeMetadataInput(...)
        >>> metadata = coordinator.create_bronze_metadata(bronze_input)
    """

    # Class-level cache for environment metadata (shared across instances)
    _cached_environment: EnvironmentMetadata | None = None

    def __init__(self, run_context: RunContext) -> None:
        """Initialize coordinator with run context.

        Args:
            run_context: Immutable context for the pipeline run.
        """
        self._context = run_context

    @property
    def run_context(self) -> RunContext:
        """Access the run context."""
        return self._context

    @cached_property
    def _run_type_enum(self) -> RunTypeEnum:
        """Map domain RunType to metadata RunTypeEnum."""
        mapping = {
            RunType.INCREMENTAL: RunTypeEnum.INCREMENTAL,
            RunType.BACKFILL: RunTypeEnum.BACKFILL,
            RunType.REBUILD: RunTypeEnum.REBUILD,
        }
        return mapping.get(self._context.run_type, RunTypeEnum.INCREMENTAL)

    @classmethod
    def _get_environment_metadata(cls) -> EnvironmentMetadata:
        """Get cached environment metadata (computed once per process).

        Environment metadata (hostname, python_version, bioetl_version) is
        immutable during process lifetime, so we cache it at class level.
        """
        if cls._cached_environment is None:
            cls._cached_environment = EnvironmentMetadata(
                hostname=socket.gethostname(),
                python_version=platform.python_version(),
                bioetl_version=_get_bioetl_version(),
            )
        return cls._cached_environment

    def _build_runtime_metadata(
        self,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        duration_seconds: float | None = None,
    ) -> RuntimeMetadata:
        """Build RuntimeMetadata with consistent run_id and run_type.

        Args:
            started_at: Override start time (defaults to context.started_at).
            completed_at: Completion timestamp.
            duration_seconds: Operation duration.

        Returns:
            RuntimeMetadata with run context data.
        """
        return RuntimeMetadata(
            run_id=str(self._context.run_id),
            run_type=self._run_type_enum,
            started_at_utc=started_at or self._context.started_at,
            completed_at_utc=completed_at,
            duration_seconds=duration_seconds,
        )

    def _build_pipeline_metadata(self) -> PipelineMetadata:
        """Build PipelineMetadata from run context.

        Returns:
            PipelineMetadata with pipeline identification.
        """
        return PipelineMetadata(
            name=self._context.pipeline_name,
            provider=self._context.provider,
            entity=self._context.entity,
        )

    def create_bronze_metadata(self, input_data: BronzeMetadataInput) -> BronzeMetadata:
        """Create Bronze layer metadata.

        Args:
            input_data: Bronze-specific metadata inputs.

        Returns:
            Complete BronzeMetadata for sidecar file.
        """
        duration = (input_data.completed_at - input_data.started_at).total_seconds()

        # Build source metadata with query_string
        if input_data.source_metadata is not None:
            source = input_data.source_metadata
            # Inject query_string if provided and not already set in source_metadata
            if input_data.query_string and source.query_string is None:
                source = source.model_copy(
                    update={"query_string": input_data.query_string}
                )
        else:
            # Create minimal SourceMetadata with query_string
            source = SourceMetadata(
                type="api",
                query_string=input_data.query_string,
            )

        return BronzeMetadata(
            runtime=self._build_runtime_metadata(
                started_at=input_data.started_at,
                completed_at=input_data.completed_at,
                duration_seconds=duration,
            ),
            pipeline=self._build_pipeline_metadata(),
            source=source,
            output=OutputMetadata(
                files=[
                    FileOutputMetadata(
                        path=input_data.output_path,
                        size_bytes=input_data.compressed_size,
                        record_count=input_data.record_count,
                    )
                ],
                total_records=input_data.record_count,
                total_bytes=input_data.compressed_size,
            ),
            environment=self._get_environment_metadata(),
        )

    def create_silver_metadata(self, input_data: SilverMetadataInput) -> SilverMetadata:
        """Create Silver layer metadata.

        Args:
            input_data: Silver-specific metadata inputs.

        Returns:
            Complete SilverMetadata for sidecar file.
        """
        if not input_data.records:
            raise ValueError("Cannot create Silver metadata without records")

        # Build lineage from records and bronze_refs
        source_batch_ids = list(
            {
                r.get("_source_batch_id", "")
                for r in input_data.records
                if r.get("_source_batch_id")
            }
        )

        bronze_paths: list[str] = []
        if input_data.bronze_refs:
            bronze_paths = [ref.relative_path for ref in input_data.bronze_refs]

        # Get transform info: prioritize input_data, fallback to RunContext
        transform_version = (
            input_data.transform_version
            if input_data.transform_version is not None
            else self._context.transform_version
        )
        transform_steps = list(
            input_data.transform_steps
            if input_data.transform_steps is not None
            else self._context.transform_steps
        )

        lineage = LineageMetadata(
            source_batch_ids=source_batch_ids,
            bronze_paths=bronze_paths,
            transform_version=transform_version,
            transform_steps=transform_steps,
        )

        # Map SilverWriteMode to DeltaMetrics operation
        operation_map: dict[
            SilverWriteMode, Literal["merge", "overwrite", "append"]
        ] = {
            SilverWriteMode.MERGE: "merge",
            SilverWriteMode.APPEND: "append",
            SilverWriteMode.DELETE: "overwrite",
        }

        delta = DeltaMetrics(
            table_path=input_data.table_path,
            operation=operation_map[input_data.mode],
            primary_key=input_data.primary_keys,
            version_after=input_data.version_after,
            rows_inserted=len(input_data.records),
        )

        # Build DQ summary from computed metrics or use basic fallback
        if input_data.dq_metrics is not None:
            dq_summary = input_data.dq_metrics.to_dq_summary()
        else:
            dq_summary = DQSummary(
                total_records=len(input_data.records),
                valid_records=len(input_data.records),
            )

        output = SilverOutputMetadata(
            record_count=len(input_data.records),
        )

        return SilverMetadata(
            runtime=self._build_runtime_metadata(),
            pipeline=self._build_pipeline_metadata(),
            lineage=lineage,
            delta=delta,
            dq_summary=dq_summary,
            output=output,
            environment=self._get_environment_metadata(),
            dq_report_path=input_data.dq_report_path,
        )

    def _extract_schema_metadata(self, gold_schema: Any | None) -> SchemaMetadata:
        """Extract schema metadata from a Pandera DataFrameModel.

        Extracts contract_path, version, columns, and validation mode from
        the Pandera schema class for Gold layer metadata tracking.

        Args:
            gold_schema: Pandera DataFrameModel class (not instance).

        Returns:
            SchemaMetadata with populated fields, or default if schema is None.
        """
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
        except Exception:
            pass

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
        except Exception:
            # If schema extraction fails, leave columns empty
            pass

        return SchemaMetadata(
            contract_path=contract_path,
            version=version,
            validation=validation,
            columns=columns,
        )

    def create_gold_metadata(self, input_data: GoldMetadataInput) -> GoldMetadata:
        """Create Gold layer metadata.

        Args:
            input_data: Gold-specific metadata inputs.

        Returns:
            Complete GoldMetadata for sidecar file.
        """
        if not input_data.records:
            raise ValueError("Cannot create Gold metadata without records")

        # Build lineage from Silver refs (REQ-LINEAGE-002: Silver → Gold tracking)
        source_tables: dict[str, int] = {}
        if input_data.silver_refs:
            source_tables = {
                ref.table_name: ref.delta_version for ref in input_data.silver_refs
            }

        # Get transform info: prioritize input_data, fallback to RunContext
        transform_version = (
            input_data.transform_version
            if input_data.transform_version is not None
            else self._context.transform_version
        )
        transform_steps = list(
            input_data.transform_steps
            if input_data.transform_steps is not None
            else self._context.transform_steps
        )

        lineage = LineageMetadata(
            source_tables=source_tables,
            transform_version=transform_version,
            transform_steps=transform_steps,
        )

        # Build DQ summary (basic metrics)
        dq_summary = DQSummary(
            total_records=len(input_data.records),
            valid_records=len(input_data.records),
        )

        # Build output metrics
        output = GoldOutputMetadata(
            record_count=len(input_data.records),
        )

        # Build SCD metadata if applicable
        scd = None
        if input_data.mode == GoldWriteMode.SCD2 and input_data.scd_config:
            scd = SCDMetadata(
                enabled=True,
                effective_date_column=input_data.scd_config.get(
                    "valid_from_col", "_valid_from"
                ),
                end_date_column=input_data.scd_config.get("valid_to_col", "_valid_to"),
                current_flag_column=input_data.scd_config.get(
                    "current_flag_col", "_is_current"
                ),
            )

        # Extract schema metadata from Gold schema (contract_path, version, columns)
        schema_info = self._extract_schema_metadata(input_data.gold_schema)

        return GoldMetadata(
            runtime=self._build_runtime_metadata(
                completed_at=input_data.completed_at,
            ),
            pipeline=self._build_pipeline_metadata(),
            lineage=lineage,
            schema_info=schema_info,
            dq_summary=dq_summary,
            output=output,
            scd=scd,
            environment=self._get_environment_metadata(),
        )

    @classmethod
    def reset_environment_cache(cls) -> None:
        """Reset the environment metadata cache (useful for testing)."""
        cls._cached_environment = None
