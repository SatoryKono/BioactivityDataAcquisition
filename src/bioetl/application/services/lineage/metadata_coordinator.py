"""Centralized Metadata Coordinator Service."""

from __future__ import annotations

from datetime import datetime
from functools import cached_property

from bioetl.application.services.lineage._metadata_coordinator_helpers import (
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
from bioetl.application.services.lineage.metadata_coordinator_bronze import (
    create_bronze_lineage_sidecar_payload,
    create_bronze_metadata_payload,
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
    BronzeMetadata,
    EnvironmentMetadata,
    GoldMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    SilverMetadata,
)
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
    """Centralized coordinator for metadata creation across Medallion layers."""

    def __init__(self, run_context: RunContext) -> None:
        """Initialize coordinator with immutable run context."""
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
        """Get cached environment metadata computed once per process."""
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
        """Build RuntimeMetadata with consistent run_id and run_type."""
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
        """Create Bronze layer metadata."""
        return create_bronze_metadata_payload(
            run_context=self._context,
            metadata_assembler=self._metadata_assembler,
            input_data=input_data,
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
        return create_bronze_lineage_sidecar_payload(
            run_context=self._context,
            provider=provider,
            entity=entity,
            batch_id=batch_id,
            ingestion_ts=ingestion_ts,
        )

    def create_silver_metadata(self, input_data: SilverMetadataInput) -> SilverMetadata:
        """Create Silver layer metadata."""
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
        """Create Gold layer metadata."""
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
