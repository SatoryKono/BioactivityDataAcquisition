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

import platform
import socket
from datetime import datetime
from functools import cached_property
from typing import ClassVar, Final

from bioetl.application.services.metadata_assemblers import (
    GoldMetadataAssembler,
    SilverMetadataAssembler,
)
from bioetl.domain.models.metadata import (
    BaseOutputMetadata,
    BronzeMetadata,
    BronzeOutputExt,
    EnvironmentMetadata,
    FileOutputMetadata,
    GoldMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    RunTypeEnum,
    SilverMetadata,
    SourceMetadata,
)
from bioetl.domain.ports import (
    BronzeMetadataInput,
    GoldMetadataInput,
    MetadataCoordinatorPort,
    SilverMetadataInput,
)
from bioetl.domain.types import RunType
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.domain.version import get_version as _get_bioetl_version

__all__ = [
    "MetadataCoordinator",
]

_RUN_TYPE_TO_ENUM: Final[dict[RunType, RunTypeEnum]] = {
    RunType.INCREMENTAL: RunTypeEnum.INCREMENTAL,
    RunType.BACKFILL: RunTypeEnum.BACKFILL,
    RunType.REBUILD: RunTypeEnum.REBUILD,
}


class MetadataCoordinator(MetadataCoordinatorPort):
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
    _cached_environment: ClassVar[EnvironmentMetadata | None] = None

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
        return _RUN_TYPE_TO_ENUM[self._context.run_type]

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
            manifest_id=self._context.manifest_id,
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

    @cached_property
    def _silver_assembler(self) -> SilverMetadataAssembler:
        """Build Silver metadata assembler once per coordinator instance."""
        return SilverMetadataAssembler(
            run_context=self._context,
            runtime_metadata_factory=self._build_runtime_metadata,
            pipeline_metadata_factory=self._build_pipeline_metadata,
            environment_metadata=self._get_environment_metadata(),
        )

    @cached_property
    def _gold_assembler(self) -> GoldMetadataAssembler:
        """Build Gold metadata assembler once per coordinator instance."""
        return GoldMetadataAssembler(
            run_context=self._context,
            runtime_metadata_factory=self._build_runtime_metadata,
            pipeline_metadata_factory=self._build_pipeline_metadata,
            environment_metadata=self._get_environment_metadata(),
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
        return self._silver_assembler.assemble(input_data)

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
        return self._gold_assembler.assemble(input_data)

    @classmethod
    def reset_environment_cache(cls) -> None:
        """Reset the environment metadata cache (useful for testing)."""
        cls._cached_environment = None
