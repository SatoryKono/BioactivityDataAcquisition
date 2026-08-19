"""Protection resolver for file-backed control-plane lifecycle planning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from bioetl.domain.control_plane import ControlPlaneArtifactLifecyclePolicy
from bioetl.infrastructure.control_plane._file_artifact_lifecycle_manifest_protections import (
    collect_manifest_protections,
)
from bioetl.infrastructure.control_plane._file_artifact_lifecycle_runtime_protections import (
    collect_checkpoint_protections,
    collect_lineage_protections,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_types import (
    _ProtectedRefs,
)


@dataclass(slots=True)
class ProtectedRefAccumulator:
    """Mutable protected-reference accumulator used during planning."""

    manifest_ids: set[str]
    run_ids: set[str]
    input_snapshot_ids: set[str]
    effective_config_artifact_ids: set[str]
    lineage_fragment_ids: set[str]
    evidence_floor_manifest_ids: set[str]
    evidence_floor_run_ids: set[str]
    evidence_floor_input_snapshot_ids: set[str]
    evidence_floor_effective_config_artifact_ids: set[str]
    evidence_floor_lineage_fragment_ids: set[str]

    @classmethod
    def from_policy(
        cls,
        policy: ControlPlaneArtifactLifecyclePolicy,
    ) -> ProtectedRefAccumulator:
        return cls(
            manifest_ids=set(policy.protected_manifest_ids),
            run_ids=set(policy.protected_run_ids),
            input_snapshot_ids=set(policy.protected_input_snapshot_ids),
            effective_config_artifact_ids=set(
                policy.protected_effective_config_artifact_ids
            ),
            lineage_fragment_ids=set(policy.protected_lineage_fragment_ids),
            evidence_floor_manifest_ids=set(),
            evidence_floor_run_ids=set(),
            evidence_floor_input_snapshot_ids=set(),
            evidence_floor_effective_config_artifact_ids=set(),
            evidence_floor_lineage_fragment_ids=set(),
        )

    def freeze(self) -> _ProtectedRefs:
        return _ProtectedRefs(
            manifest_ids=frozenset(self.manifest_ids),
            run_ids=frozenset(self.run_ids),
            input_snapshot_ids=frozenset(self.input_snapshot_ids),
            effective_config_artifact_ids=frozenset(self.effective_config_artifact_ids),
            lineage_fragment_ids=frozenset(self.lineage_fragment_ids),
            evidence_floor_manifest_ids=frozenset(self.evidence_floor_manifest_ids),
            evidence_floor_run_ids=frozenset(self.evidence_floor_run_ids),
            evidence_floor_input_snapshot_ids=frozenset(
                self.evidence_floor_input_snapshot_ids
            ),
            evidence_floor_effective_config_artifact_ids=frozenset(
                self.evidence_floor_effective_config_artifact_ids
            ),
            evidence_floor_lineage_fragment_ids=frozenset(
                self.evidence_floor_lineage_fragment_ids
            ),
        )


def resolve_protected_refs(
    *,
    base_path: Path,
    policy: ControlPlaneArtifactLifecyclePolicy,
    cutoff: datetime,
) -> _ProtectedRefs:
    """Resolve explicit and live-reference protections before planning."""
    refs = ProtectedRefAccumulator.from_policy(policy)
    collect_manifest_protections(
        base_path=base_path,
        cutoff=cutoff,
        refs=refs,
        allow_profile_floor_violation=policy.allow_profile_floor_violation,
    )
    collect_checkpoint_protections(base_path=base_path, cutoff=cutoff, refs=refs)
    collect_lineage_protections(base_path=base_path, refs=refs)
    return refs.freeze()


def resolve_protected_refs_for_manifest(
    *,
    manifest: object,
    policy: ControlPlaneArtifactLifecyclePolicy,
) -> _ProtectedRefs:
    """Build protections from one selected manifest without catalog scans."""
    refs = ProtectedRefAccumulator.from_policy(policy)
    manifest_id = str(getattr(manifest, "manifest_id", "") or "")
    if manifest_id:
        refs.manifest_ids.add(manifest_id)
    run_id = getattr(manifest, "run_id", None)
    if run_id is not None:
        refs.run_ids.add(str(run_id))
    provenance = getattr(manifest, "code_provenance", None)
    artifact_id = getattr(provenance, "effective_config_artifact_id", None)
    if isinstance(artifact_id, str) and artifact_id.strip():
        refs.effective_config_artifact_ids.add(artifact_id.strip())
    for source in getattr(manifest, "source_refs", ()) or ():
        for snapshot in getattr(source, "input_snapshots", ()) or ():
            snapshot_id = getattr(snapshot, "snapshot_id", None)
            if isinstance(snapshot_id, str) and snapshot_id.strip():
                refs.input_snapshot_ids.add(snapshot_id.strip())
    return refs.freeze()
