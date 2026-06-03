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

from datetime import datetime
from functools import cached_property

from bioetl.application.services.lineage._metadata_coordinator_helpers import (
    build_bronze_file_output_metadata,
    build_bronze_output_content_hash,
    build_bronze_source_metadata,
    create_metadata_bundle,
    validate_records_present,
)
from bioetl.application.services.lineage.metadata_assemblers import (
    GoldMetadataService,
    SilverMetadataService,
)
from bioetl.application.services.lineage.metadata_context import (
    EnvironmentMetadataRuntimeService,
    RunMetadataAssembler,
)
from bioetl.application.services.lineage.metadata_lineage_fragments import (
    build_bronze_lineage_fragment,
    build_gold_lineage_fragment,
    build_silver_lineage_fragment,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)
from bioetl.domain.lineage import LineageGraphFragment, MetadataLineageBundleResult
from bioetl.domain.models.metadata import (
    BaseOutputMetadata,
    BronzeMetadata,
    BronzeOutputExt,
    EnvironmentMetadata,
    GoldMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    SilverMetadata,
)
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint
from bioetl.domain.ports import (
    BronzeMetadataInput,
    GoldMetadataInput,
    MetadataCoordinatorPort,
    SilverMetadataInput,
)
from bioetl.domain.types import BatchID
from bioetl.domain.value_objects.run_context import RunContext

__all__ = [
    "MetadataCoordinator",
]


class MetadataCoordinator(MetadataCoordinatorPort):
    """Centralized coordinator for metadata creation across Medallion layers.

    Creates consistent metadata with shared run_id, timestamps, and pipeline
    identification. Environment metadata is computed once and cached.

    Example:
        >>> from datetime import UTC, datetime
        >>> from uuid import UUID
        >>> context = RunContext.create(
        ...     run_id=RunID(UUID("00000000-0000-0000-0000-000000000301")),
        ...     run_type=RunType.INCREMENTAL,
        ...     started_at=datetime.now(UTC),
        ...     provider="chembl",
        ...     entity="activity",
        ... )
        >>> coordinator = MetadataCoordinator(context)
        >>> bronze_input = BronzeMetadataInput(...)
        >>> metadata = coordinator.create_bronze_metadata(bronze_input)
    """

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

    def _strict_manifest_id_required(self) -> bool:
        """Return whether sidecar lineage must close over manifest identity."""
        profile = str(self._context.required_persistence_profile or "").strip().lower()
        return (
            bool(self._context.exact_replay) or profile in STRICT_PERSISTENCE_PROFILES
        )

    @classmethod
    def _get_environment_metadata(cls) -> EnvironmentMetadata:
        """Get cached environment metadata (computed once per process).

        Environment metadata (hostname, python_version, bioetl_version) is
        immutable during process lifetime, so we cache it at class level.
        """
        return EnvironmentMetadataRuntimeService.get()

    @cached_property
    def _metadata_assembler(self) -> RunMetadataAssembler:
        """Build the metadata assembler lazily to avoid inline DI instantiation."""
        return RunMetadataAssembler(self._context)

    def _build_runtime_metadata(
        self,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        duration_seconds: float | None = None,
        input_snapshot_fingerprint: str | None = None,
    ) -> RuntimeMetadata:
        """Build RuntimeMetadata with consistent run_id and run_type.

        Args:
            started_at: Override start time (defaults to context.started_at).
            completed_at: Completion timestamp.
            duration_seconds: Operation duration.

        Returns:
            RuntimeMetadata with run context data.
        """
        return self._metadata_assembler.build_runtime_metadata(
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            input_snapshot_fingerprint=input_snapshot_fingerprint,
        )

    def _build_pipeline_metadata(self) -> PipelineMetadata:
        """Build PipelineMetadata with versioning from run context."""
        return self._metadata_assembler.build_pipeline_metadata()

    @cached_property
    def _silver_metadata_service(self) -> SilverMetadataService:
        """Build Silver metadata service once per coordinator instance."""
        return SilverMetadataService(
            run_context=self._context,
            runtime_metadata_builder=self._build_runtime_metadata,
            pipeline_metadata_builder=self._build_pipeline_metadata,
            environment_metadata=self._metadata_assembler.environment_metadata,
        )

    @cached_property
    def _gold_metadata_service(self) -> GoldMetadataService:
        """Build Gold metadata service once per coordinator instance."""
        return GoldMetadataService(
            run_context=self._context,
            runtime_metadata_builder=self._build_runtime_metadata,
            pipeline_metadata_builder=self._build_pipeline_metadata,
            environment_metadata=self._metadata_assembler.environment_metadata,
        )

    def create_bronze_metadata(self, input_data: BronzeMetadataInput) -> BronzeMetadata:
        """Create Bronze layer metadata.

        Args:
            input_data: Bronze-specific metadata inputs.

        Returns:
            Complete BronzeMetadata for sidecar file.
        """
        duration = (input_data.completed_at - input_data.started_at).total_seconds()
        source = build_bronze_source_metadata(input_data)
        file_metadata = build_bronze_file_output_metadata(input_data)
        source_snapshot_fingerprint = compute_input_snapshot_identity_fingerprint(
            list(source.input_snapshots)
        )

        return BronzeMetadata(
            runtime=self._build_runtime_metadata(
                started_at=input_data.started_at,
                completed_at=input_data.completed_at,
                duration_seconds=duration,
                input_snapshot_fingerprint=source_snapshot_fingerprint,
            ),
            pipeline=self._build_pipeline_metadata(),
            source=source,
            output=BaseOutputMetadata(
                artifact_id=f"bronze_batch:{input_data.batch_id}",
                record_count=input_data.record_count,
                total_bytes=input_data.compressed_size,
                content_hash=build_bronze_output_content_hash(input_data),
                write_started_at=input_data.started_at,
                write_completed_at=input_data.completed_at,
            ),
            output_ext=BronzeOutputExt(
                files=[file_metadata],
            ),
            environment=self._get_environment_metadata(),
            governance=input_data.governance,
        )

    def build_bronze_lineage_fragment(
        self,
        input_data: BronzeMetadataInput,
    ) -> LineageGraphFragment:
        """Build canonical Bronze lineage fragment without changing sidecar API."""
        return build_bronze_lineage_fragment(
            run_context=self._context,
            input_data=input_data,
        )

    def create_bronze_metadata_bundle(
        self,
        input_data: BronzeMetadataInput,
    ) -> MetadataLineageBundleResult[BronzeMetadata]:
        """Create Bronze sidecar metadata bundled with canonical lineage fragment."""
        return create_metadata_bundle(
            metadata=self.create_bronze_metadata(input_data),
            lineage_fragment=self.build_bronze_lineage_fragment(input_data),
            strict_manifest_id_required=self._strict_manifest_id_required(),
        )

    def create_bronze_lineage_sidecar(
        self,
        *,
        provider: str,
        entity: str,
        batch_id: BatchID,
        ingestion_ts: datetime,
    ) -> dict[str, str]:
        """Project canonical Bronze runtime anchors for the legacy `.meta.json` sidecar."""
        # Use the provider/entity from the request, not the context
        # This allows the MetadataCoordinator to be reused across pipelines
        return {
            "run_id": str(self._context.run_id),
            "manifest_id": self._context.manifest_id or "",
            "run_type": self._context.run_type.value,
            "ingestion_ts": ingestion_ts.isoformat(),
            "provider": provider,
            "entity": entity,
            "batch_id": str(batch_id),
            "execution_fingerprint": self._context.execution_fingerprint or "",
            "effective_config_hash": self._context.effective_config_hash or "",
            "effective_config_artifact_id": (
                self._context.effective_config_artifact_id or ""
            ),
            "contract_ref": self._context.contract_ref or "",
            "contract_version": self._context.contract_version or "",
            "required_persistence_profile": (
                self._context.required_persistence_profile or ""
            ),
            "sidecar_truth_boundary": "legacy_lineage_projection_non_authoritative",
            "authoritative_replay_artifacts": (
                "run_manifest,lineage_fragment,layer_metadata,effective_config_artifact"
            ),
        }

    def create_silver_metadata(self, input_data: SilverMetadataInput) -> SilverMetadata:
        """Create Silver layer metadata.

        Args:
            input_data: Silver-specific metadata inputs.

        Returns:
            Complete SilverMetadata for sidecar file.
        """
        validate_records_present(
            records=input_data.records,
            total_records=input_data.total_records,
            layer_name="Silver",
        )
        return self._silver_metadata_service.assemble(input_data)

    def build_silver_lineage_fragment(
        self,
        input_data: SilverMetadataInput,
    ) -> LineageGraphFragment:
        """Build canonical Silver lineage fragment without changing sidecar API."""
        validate_records_present(
            records=input_data.records,
            total_records=input_data.total_records,
            layer_name="Silver",
        )
        return build_silver_lineage_fragment(
            run_context=self._context,
            input_data=input_data,
        )

    def create_silver_metadata_bundle(
        self,
        input_data: SilverMetadataInput,
    ) -> MetadataLineageBundleResult[SilverMetadata]:
        """Create Silver sidecar metadata bundled with canonical lineage fragment."""
        return create_metadata_bundle(
            metadata=self.create_silver_metadata(input_data),
            lineage_fragment=self.build_silver_lineage_fragment(input_data),
            strict_manifest_id_required=self._strict_manifest_id_required(),
        )

    def create_gold_metadata(self, input_data: GoldMetadataInput) -> GoldMetadata:
        """Create Gold layer metadata.

        Args:
            input_data: Gold-specific metadata inputs.

        Returns:
            Complete GoldMetadata for sidecar file.
        """
        validate_records_present(
            records=input_data.records,
            total_records=input_data.total_records,
            layer_name="Gold",
        )
        return self._gold_metadata_service.assemble(input_data)

    def build_gold_lineage_fragment(
        self,
        input_data: GoldMetadataInput,
    ) -> LineageGraphFragment:
        """Build canonical Gold lineage fragment without changing sidecar API."""
        validate_records_present(
            records=input_data.records,
            total_records=input_data.total_records,
            layer_name="Gold",
        )
        return build_gold_lineage_fragment(
            run_context=self._context,
            input_data=input_data,
        )

    def create_gold_metadata_bundle(
        self,
        input_data: GoldMetadataInput,
    ) -> MetadataLineageBundleResult[GoldMetadata]:
        """Create Gold sidecar metadata bundled with canonical lineage fragment."""
        return create_metadata_bundle(
            metadata=self.create_gold_metadata(input_data),
            lineage_fragment=self.build_gold_lineage_fragment(input_data),
            strict_manifest_id_required=self._strict_manifest_id_required(),
        )

    @classmethod
    def reset_environment_cache(cls) -> None:
        """Reset the environment metadata cache (useful for testing)."""
        EnvironmentMetadataRuntimeService.reset()
