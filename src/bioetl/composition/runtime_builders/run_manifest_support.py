"""Run-manifest construction and propagation into the composed execution context."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.composition.runtime_builders._run_context_values import (
    resolve_run_context_values,
)
from bioetl.composition.runtime_builders._run_manifest_context_updates import (
    apply_manifest_updates_to_mutable_context,
    build_dataclass_manifest_updates,
    extract_optional_updates_from_refs,
    iter_optional_control_plane_updates,
    iter_optional_control_plane_updates_from_mapping,
)
from bioetl.composition.runtime_builders._run_manifest_refs import (
    ManifestControlPlaneRefs,
    build_planned_artifacts,
    build_run_source_refs,
    control_plane_root,
    create_control_plane_refs,
)
from bioetl.composition.runtime_builders._run_manifest_replay_support import (
    resolve_replay_parentage,
)
from bioetl.composition.runtime_builders._run_manifest_sink_policy import (
    validate_reproducible_sink_modes,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_support import (
    build_launch_context_snapshot,
    resolve_provider_entity,
    to_serializable_mapping,
)
from bioetl.composition.runtime_builders.input_snapshot_resolution import (
    resolve_pipeline_input_snapshot_refs,
)
from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
    RunManifestContractIdentity,
    resolve_contract_identity,
)
from bioetl.domain.control_plane import ReplayCapability, RunSourceRef
from bioetl.domain.control_plane.reproducibility_policy import (
    resolve_replay_capability as _resolve_replay,
)

__all__ = [
    "ManifestControlPlaneRefs",
    "RunManifestContractIdentity",
    "RunManifestProvenanceBundle",
    "apply_manifest_updates_to_mutable_context",
    "build_dataclass_manifest_updates",
    "build_launch_context_snapshot",
    "build_planned_artifacts",
    "build_run_manifest_provenance_bundle",
    "build_run_source_refs",
    "control_plane_root",
    "create_control_plane_refs",
    "extract_optional_updates_from_refs",
    "iter_optional_control_plane_updates",
    "iter_optional_control_plane_updates_from_mapping",
    "resolve_contract_identity",
    "resolve_pipeline_input_snapshot_refs",
    "resolve_provider_entity",
    "resolve_replay_capability",
    "resolve_replay_parentage",
    "resolve_run_context_values",
    "to_serializable_mapping",
    "validate_reproducible_sink_modes",
]


@dataclass(frozen=True, slots=True)
class RunManifestProvenanceBundle:
    """Effective-config provenance bundle passed into manifest creation."""

    effective_config_artifact_id: str
    resolved_config_hash: str
    effective_config_hash: str
    source_fingerprint: str | None
    dq_contract_compatibility_hash: str


def build_run_manifest_provenance_bundle(
    artifact_result: tuple[str, str, str, str | None, str],
) -> RunManifestProvenanceBundle:
    """Convert one persisted effective-config result tuple into manifest provenance."""
    (
        effective_config_artifact_id,
        resolved_config_hash,
        effective_config_hash,
        source_fingerprint,
        dq_contract_compatibility_hash,
    ) = artifact_result
    return RunManifestProvenanceBundle(
        effective_config_artifact_id=effective_config_artifact_id,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        source_fingerprint=source_fingerprint,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
    )


def resolve_replay_capability(
    *,
    source_refs: tuple[RunSourceRef, ...],
    resume_requested: bool,
) -> ReplayCapability:
    return _resolve_replay(source_refs=source_refs, resume_requested=resume_requested)
