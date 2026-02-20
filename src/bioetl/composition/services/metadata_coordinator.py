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

import ast
import inspect
import platform
import socket
from datetime import datetime
from functools import cached_property
from typing import Any, Literal

from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.domain.models.metadata import (
    BaseOutputMetadata,
    BronzeMetadata,
    BronzeOutputExt,
    CompositeOutputExt,
    CompositeSchemaValidationMetadata,
    DeltaMetrics,
    DQSummary,
    EnvironmentMetadata,
    FileOutputMetadata,
    GoldMetadata,
    GoldOutputExt,
    LineageMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    RunTypeEnum,
    SCDMetadata,
    SchemaColumnMetadata,
    SchemaMetadata,
    SilverMetadata,
    SilverOutputExt,
    SourceMetadata,
)
from bioetl.domain.ports import (
    BronzeMetadataInput,
    GoldMetadataInput,
    SilverMetadataInput,
)
from bioetl.domain.types import RunType
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.domain.version import get_version as _get_bioetl_version


def _parse_composite_list(value: Any) -> list[str]:
    """Parse composite list metadata stored as list or stringified list."""
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return []
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return []


def _parse_composite_status(value: Any) -> dict[str, str]:
    """Parse enrichment status stored as dict or stringified dict."""
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return {}
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}
    return {}


def _extract_composite_output_ext(
    records: list[dict[str, Any]],
    partition_count: int,
    *,
    schema_validation_enabled: bool = False,
    schema_validation_strict: bool | None = None,
) -> CompositeOutputExt | None:
    """Extract composite output metadata from merged Gold records."""
    if not records:
        return None

    sample = records[0]
    composite_run_id = sample.get("_composite_run_id")
    lineage_raw = sample.get("_lineage_created_at")
    lineage_created_at: datetime | None = None
    if isinstance(lineage_raw, str):
        try:
            lineage_created_at = datetime.fromisoformat(lineage_raw)
        except ValueError:
            lineage_created_at = None

    has_composite_fields = any(key.startswith("_composite_") for key in sample)
    has_lineage_fields = "_source_providers" in sample or "_enrichment_status" in sample
    if not has_composite_fields and not has_lineage_fields:
        return None

    return CompositeOutputExt(
        partition_count=partition_count,
        composite_run_id=str(composite_run_id)
        if composite_run_id is not None
        else None,
        source_providers=_parse_composite_list(sample.get("_source_providers")),
        enrichment_status=_parse_composite_status(sample.get("_enrichment_status")),
        lineage_created_at=lineage_created_at,
        schema_validation=CompositeSchemaValidationMetadata(
            enabled=schema_validation_enabled,
            strict=schema_validation_strict,
            status="passed" if schema_validation_enabled else "not_run",
        ),
    )


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
        """Build PipelineMetadata with versioning from run context."""
        return PipelineMetadata(
            name=self._context.pipeline_name,
            provider=self._context.provider,
            entity=self._context.entity,
            version=self._context.pipeline_version or "1.0.0",
            git_commit=self._context.git_commit,
            config_hash=self._context.config_hash,
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

        # Build file metadata for output_ext
        file_metadata = FileOutputMetadata(
            path=input_data.output_path,
            size_bytes=input_data.compressed_size,
            record_count=input_data.record_count,
        )

        return BronzeMetadata(
            runtime=self._build_runtime_metadata(
                started_at=input_data.started_at,
                completed_at=input_data.completed_at,
                duration_seconds=duration,
            ),
            pipeline=self._build_pipeline_metadata(),
            source=source,
            output=BaseOutputMetadata(
                record_count=input_data.record_count,
                total_bytes=input_data.compressed_size,
                write_started_at=input_data.started_at,
                write_completed_at=input_data.completed_at,
            ),
            output_ext=BronzeOutputExt(
                files=[file_metadata],
            ),
            environment=self._get_environment_metadata(),
            governance=input_data.governance,
        )

    def create_silver_metadata(self, input_data: SilverMetadataInput) -> SilverMetadata:
        """Create Silver layer metadata.

        Args:
            input_data: Silver-specific metadata inputs.

        Returns:
            Complete SilverMetadata for sidecar file.
        """
        # Validate records (REQ-METADATA-001)
        if not input_data.records and input_data.total_records is None:
            raise ValueError("Cannot create Silver metadata without records")

        # Build lineage from records and bronze_refs
        if input_data.source_batch_ids is not None:
            source_batch_ids = input_data.source_batch_ids
        elif input_data.records:
            source_batch_ids = list(
                {
                    r.get("_source_batch_id", "")
                    for r in input_data.records
                    if r.get("_source_batch_id")
                }
            )
        else:
            source_batch_ids = []

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
            partition_by=input_data.partition_by or [],
            version_after=input_data.version_after,
            rows_inserted=input_data.total_records
            if input_data.total_records is not None
            else len(input_data.records or []),
        )

        # Build DQ summary from computed metrics or use basic fallback
        rec_count = (
            input_data.total_records
            if input_data.total_records is not None
            else len(input_data.records or [])
        )
        dq_summary = (
            input_data.dq_metrics.to_dq_summary()
            if input_data.dq_metrics
            else DQSummary(total_records=rec_count, valid_records=rec_count)
        )
        if input_data.dq_rule_provenance:
            dq_summary = dq_summary.model_copy(
                update={"rule_provenance": input_data.dq_rule_provenance}
            )

        # Calculate duration if both timestamps provided
        duration_seconds = (
            (input_data.completed_at - input_data.started_at).total_seconds()
            if input_data.started_at and input_data.completed_at
            else None
        )

        # Build unified output metadata (ADR-029)
        output = BaseOutputMetadata(
            record_count=rec_count or 0,
            total_bytes=getattr(input_data, "total_bytes", 0) or 0,
            write_started_at=input_data.started_at,
            write_completed_at=input_data.completed_at,
        )

        # Build Silver-specific output extension with delta versions
        output_ext = SilverOutputExt(
            delta_version_before=getattr(input_data, "version_before", None),
            delta_version_after=input_data.version_after,
        )

        return SilverMetadata(
            runtime=self._build_runtime_metadata(
                started_at=input_data.started_at,
                completed_at=input_data.completed_at,
                duration_seconds=duration_seconds or 0.0,
            ),
            pipeline=self._build_pipeline_metadata(),
            lineage=lineage,
            delta=delta,
            dq_summary=dq_summary,
            output=output,
            output_ext=output_ext,
            environment=self._get_environment_metadata(),
            dq_report_path=input_data.dq_report_path,
            governance=input_data.governance,
        )

    # Any: Pandera DataFrameModel...
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
        except (AttributeError, OSError, TypeError):
            # Module may not have __file__ or path extraction may fail
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
                        dtype_str = (
                            str(col_schema.dtype) if col_schema.dtype else "object"
                        )
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

    def create_gold_metadata(self, input_data: GoldMetadataInput) -> GoldMetadata:
        """Create Gold layer metadata.

        Args:
            input_data: Gold-specific metadata inputs.

        Returns:
            Complete GoldMetadata for sidecar file.
        """
        # Validate records (REQ-METADATA-001)
        if not input_data.records and input_data.total_records is None:
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
        rec_count = (
            input_data.total_records
            if input_data.total_records is not None
            else len(input_data.records or [])
        )
        rec_count = rec_count or 0
        dq_summary = DQSummary(
            total_records=rec_count,
            valid_records=rec_count,
        )

        # Build unified output metadata (ADR-029)
        composite_ext = _extract_composite_output_ext(
            input_data.records or [],
            partition_count=getattr(input_data, "partition_count", 0),
            schema_validation_enabled=getattr(
                input_data, "schema_validation_enabled", False
            ),
            schema_validation_strict=getattr(
                input_data, "schema_validation_strict", None
            ),
        )

        output = BaseOutputMetadata(
            record_count=rec_count or 0,
            total_bytes=getattr(input_data, "total_bytes", 0) or 0,
            write_started_at=getattr(input_data, "started_at", None),
            write_completed_at=input_data.completed_at,
            composite_run_id=composite_ext.composite_run_id if composite_ext else None,
        )

        # Build Gold-specific/composite-specific output extension
        partition_count = getattr(input_data, "partition_count", 0)
        output_ext = composite_ext or GoldOutputExt(partition_count=partition_count)

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

        # Note: schema_info uses Field(alias="schema") with populate_by_name=True
        # mypy doesn't understand this Pydantic feature, but it works at runtime
        return GoldMetadata(  # type: ignore[call-arg]
            runtime=self._build_runtime_metadata(
                completed_at=input_data.completed_at,
                duration_seconds=0.0,  # Gold duration currently not tracked per batch
            ),
            pipeline=self._build_pipeline_metadata(),
            lineage=lineage,
            schema_info=schema_info,
            dq_summary=dq_summary,
            output=output,
            output_ext=output_ext,
            scd=scd,
            environment=self._get_environment_metadata(),
            dq_report_path=input_data.dq_report_path,
            governance=input_data.governance,
        )

    @classmethod
    def reset_environment_cache(cls) -> None:
        """Reset the environment metadata cache (useful for testing)."""
        cls._cached_environment = None
