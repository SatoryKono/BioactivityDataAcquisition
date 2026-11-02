"""Run-manifest construction and propagation into the composed execution context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.control_plane_paths import control_plane_root, resolve_data_root

from bioetl.composition.runtime_builders._run_context_values import (
    resolve_run_context_values,
)
from bioetl.composition.runtime_builders._run_manifest_refs import (
    ManifestControlPlaneRefs,
    build_run_source_refs,
    create_control_plane_refs,
)
from bioetl.composition.runtime_builders._run_manifest_replay_support import (
    resolve_replay_parentage,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_support import (
    build_launch_context_snapshot,
)
from bioetl.domain.control_plane.run_manifest_sink_policy import (
    validate_reproducible_sink_modes,
)
from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
    RunManifestContractIdentity,
    resolve_contract_identity,
)
from bioetl.domain.control_plane import ReplayCapability, RunSourceRef, RunArtifactRef
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint

if TYPE_CHECKING:
    from bioetl.domain.control_plane import RunManifest
    from bioetl.infrastructure.config.settings_api import Settings
from bioetl.domain.control_plane.reproducibility_policy import (
    resolve_replay_capability as _resolve_replay,
)

__all__ = [
    "ManifestControlPlaneRefs",
    "RunManifestContractIdentity",
    "RunManifestProvenanceBundle",
    "build_launch_context_snapshot",
    "build_planned_artifacts",
    "build_run_manifest_provenance_bundle",
    "build_run_source_refs",
    "control_plane_root",
    "create_control_plane_refs",
    "create_control_plane_refs_for_manifest",
    "resolve_contract_identity",
    "resolve_replay_capability",
    "resolve_replay_parentage",
    "resolve_run_context_values",
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


def create_control_plane_refs_for_manifest(
    *,
    manifest: RunManifest,
    provenance: RunManifestProvenanceBundle,
    contract_identity: RunManifestContractIdentity,
    required_persistence_profile: str,
) -> ManifestControlPlaneRefs:
    """Build canonical control-plane refs from one persisted manifest record."""
    input_snapshot_fingerprint = compute_input_snapshot_identity_fingerprint(
        [
            snapshot
            for source_ref in getattr(manifest, "source_refs", ())
            for snapshot in getattr(source_ref, "input_snapshots", ())
        ]
    )
    return create_control_plane_refs(
        manifest_id=manifest.manifest_id,
        execution_fingerprint=manifest.execution_fingerprint,
        resolved_config_hash=provenance.resolved_config_hash,
        effective_config_hash=provenance.effective_config_hash,
        source_fingerprint=provenance.source_fingerprint,
        dq_contract_compatibility_hash=provenance.dq_contract_compatibility_hash,
        effective_config_artifact_id=provenance.effective_config_artifact_id,
        replay_parentage=(
            getattr(manifest, "replay_of_run_id", None),
            getattr(manifest, "replay_of_manifest_id", None),
        ),
        input_snapshot_fingerprint=input_snapshot_fingerprint,
        contract=(
            contract_identity.contract_ref,
            contract_identity.contract_version,
            contract_identity.contract_schema_hash,
        ),
        policy=(
            contract_identity.dq_policy_ref,
            contract_identity.rule_bundle_version,
        ),
        normalization_profile=(
            contract_identity.normalization_profile_ref,
            contract_identity.normalization_profile_version,
            contract_identity.normalization_profile_hash,
        ),
        required_persistence_profile=required_persistence_profile,
    )


def _artifact_path_string(path: Path) -> str:
    """Return portable artifact paths with normalized separators."""
    return path.as_posix()


def build_planned_artifacts(
    *,
    settings: Settings,
    provider: str,
    entity: str,
    run_id: str | None = None,
    pipeline_name: str | None = None,
    workflow_id: str = "standalone",
    debug_export_root: str | None = None,
) -> tuple[RunArtifactRef, ...]:
    """Capture planned layer roots for the manifest control-plane snapshot."""
    output_root = resolve_data_root(settings) / "output"
    planned = [
        RunArtifactRef(
            layer="bronze",
            path=_artifact_path_string(output_root / "bronze" / provider / entity),
        ),
        RunArtifactRef(
            layer="silver",
            path=_artifact_path_string(output_root / "silver" / provider / entity),
        ),
        RunArtifactRef(
            layer="gold",
            path=_artifact_path_string(output_root / "gold" / provider / entity),
        ),
    ]
    if debug_export_root and run_id and pipeline_name:
        configured_root = Path(debug_export_root)
        if not configured_root.is_absolute():
            configured_root = Path.cwd() / configured_root
        planned.append(
            RunArtifactRef(
                layer="debug_export",
                path=_artifact_path_string(
                    configured_root / workflow_id / pipeline_name / run_id
                ),
            )
        )
    return tuple(planned)
