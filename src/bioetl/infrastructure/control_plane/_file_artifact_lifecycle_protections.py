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
