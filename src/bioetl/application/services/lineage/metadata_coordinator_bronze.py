"""Bronze metadata helpers for MetadataCoordinator."""

from __future__ import annotations

from datetime import datetime

from bioetl.application.services.lineage._metadata_coordinator_helpers import (
    build_bronze_file_output_metadata,
    build_bronze_output_content_hash,
    build_bronze_source_metadata,
)
from bioetl.application.services.lineage.metadata_context import (
    EnvironmentMetadataRuntimeService,
    RunMetadataAssembler,
)
from bioetl.domain.models.metadata import (
    BaseOutputMetadata,
    BronzeMetadata,
    BronzeOutputExt,
)
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint
from bioetl.domain.ports import BronzeMetadataInput
from bioetl.domain.types import BatchID
from bioetl.domain.value_objects.run_context import RunContext


def create_bronze_metadata_payload(
    *,
    run_context: RunContext,
    metadata_assembler: RunMetadataAssembler,
    input_data: BronzeMetadataInput,
) -> BronzeMetadata:
    """Create Bronze metadata from one coordinated run context."""
    duration = (input_data.completed_at - input_data.started_at).total_seconds()
    source = build_bronze_source_metadata(input_data)
    file_metadata = build_bronze_file_output_metadata(input_data)
    source_snapshot_fingerprint = compute_input_snapshot_identity_fingerprint(
        list(source.input_snapshots)
    )
    return BronzeMetadata(
        runtime=metadata_assembler.build_runtime_metadata(
            started_at=input_data.started_at,
            completed_at=input_data.completed_at,
            duration_seconds=duration,
            input_snapshot_fingerprint=source_snapshot_fingerprint,
        ),
        pipeline=metadata_assembler.build_pipeline_metadata(),
        source=source,
        output=BaseOutputMetadata(
            artifact_id=f"bronze_batch:{input_data.batch_id}",
            record_count=input_data.record_count,
            total_bytes=input_data.compressed_size,
            content_hash=build_bronze_output_content_hash(input_data),
            write_started_at=input_data.started_at,
            write_completed_at=input_data.completed_at,
        ),
        output_ext=BronzeOutputExt(files=[file_metadata]),
        environment=EnvironmentMetadataRuntimeService.get(),
        governance=input_data.governance,
    )


def create_bronze_lineage_sidecar_payload(
    *,
    run_context: RunContext,
    provider: str,
    entity: str,
    batch_id: BatchID,
    ingestion_ts: datetime,
) -> dict[str, str]:
    """Project canonical Bronze runtime anchors for legacy `.meta.json` sidecars."""
    return {
        "run_id": str(run_context.run_id),
        "manifest_id": run_context.manifest_id or "",
        "run_type": run_context.run_type.value,
        "ingestion_ts": ingestion_ts.isoformat(),
        "provider": provider,
        "entity": entity,
        "batch_id": str(batch_id),
        "execution_fingerprint": run_context.execution_fingerprint or "",
        "effective_config_hash": run_context.effective_config_hash or "",
        "effective_config_artifact_id": run_context.effective_config_artifact_id or "",
        "contract_ref": run_context.contract_ref or "",
        "contract_version": run_context.contract_version or "",
        "required_persistence_profile": run_context.required_persistence_profile or "",
        "sidecar_truth_boundary": "legacy_lineage_projection_non_authoritative",
        "authoritative_replay_artifacts": (
            "run_manifest,lineage_fragment,layer_metadata,effective_config_artifact"
        ),
    }


__all__ = [
    "create_bronze_lineage_sidecar_payload",
    "create_bronze_metadata_payload",
]
