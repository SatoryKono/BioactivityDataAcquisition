"""Control-plane artifact lifecycle planning models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

__all__ = [
    "ControlPlaneArtifactLifecycleApplyResult",
    "ControlPlaneArtifactLifecycleDecision",
    "ControlPlaneArtifactLifecyclePlan",
    "ControlPlaneArtifactLifecyclePolicy",
    "ControlPlaneArtifactRef",
    "ControlPlaneArtifactReplayImpact",
    "ControlPlaneArtifactResolutionIssue",
    "ControlPlaneArtifactResolutionIssueCode",
    "ControlPlaneArtifactSurface",
]


class ControlPlaneArtifactSurface(StrEnum):
    """Known file-backed control-plane artifact surfaces."""

    CACHED_BRONZE = "bronze"
    CHECKPOINT = "checkpoints"
    EFFECTIVE_CONFIG = "effective_config"
    LINEAGE = "lineage"
    RUN_LEDGER = "run_ledger"
    RUN_MANIFEST = "run_manifest"


class ControlPlaneArtifactLifecycleDecision(StrEnum):
    """Lifecycle action selected for one artifact reference."""

    DELETE = "delete"
    RETAIN = "retain"


class ControlPlaneArtifactReplayImpact(StrEnum):
    """Replay impact classification for one lifecycle artifact decision."""

    NO_REPLAY_EVIDENCE = "no_replay_evidence"
    RECOVERY_EVIDENCE_PROTECTED = "recovery_evidence_protected"
    STRICT_REPLAY_EVIDENCE_PROTECTED = "strict_replay_evidence_protected"
    UNPROTECTED_REPLAY_EVIDENCE_DELETE_CANDIDATE = (
        "unprotected_replay_evidence_delete_candidate"
    )


class ControlPlaneArtifactResolutionIssueCode(StrEnum):
    """Typed selected-run resolution failures that must not invent paths."""

    LINEAGE_INDEX_MISSING = "lineage_index_missing"
    LINEAGE_INDEX_CORRUPT = "lineage_index_corrupt"
    CHECKPOINT_INDEX_MISSING = "checkpoint_index_missing"
    CHECKPOINT_INDEX_CORRUPT = "checkpoint_index_corrupt"
    SNAPSHOT_URI_NOT_RECORDED = "snapshot_uri_not_recorded"


@dataclass(frozen=True, slots=True)
class ControlPlaneArtifactResolutionIssue:
    """One bounded selected-run resolution issue without invented paths."""

    code: ControlPlaneArtifactResolutionIssueCode
    surface: ControlPlaneArtifactSurface
    detail: str


@dataclass(frozen=True, slots=True)
class ControlPlaneArtifactLifecyclePolicy:
    """Retention and protection inputs for one lifecycle planning pass."""

    retention_days: int
    now: datetime
    protected_manifest_ids: frozenset[str] = field(default_factory=frozenset)
    protected_run_ids: frozenset[str] = field(default_factory=frozenset)
    protected_input_snapshot_ids: frozenset[str] = field(default_factory=frozenset)
    protected_effective_config_artifact_ids: frozenset[str] = field(
        default_factory=frozenset
    )
    protected_lineage_fragment_ids: frozenset[str] = field(default_factory=frozenset)
    allow_profile_floor_violation: bool = False

    def __post_init__(self) -> None:
        """Reject retention windows that would make every artifact eligible."""
        if self.retention_days < 1:
            raise ValueError("retention_days must be at least 1")


@dataclass(frozen=True, slots=True)
class ControlPlaneArtifactRef:
    """One planned lifecycle decision for a control-plane artifact file."""

    surface: ControlPlaneArtifactSurface
    path: str
    artifact_id: str
    decision: ControlPlaneArtifactLifecycleDecision
    reason: str
    created_at: datetime | None = None
    protected_by: tuple[str, ...] = ()
    replay_impact: ControlPlaneArtifactReplayImpact = (
        ControlPlaneArtifactReplayImpact.NO_REPLAY_EVIDENCE
    )

    @property
    def delete_selected(self) -> bool:
        """Return whether this artifact should be deleted during apply."""
        return self.decision is ControlPlaneArtifactLifecycleDecision.DELETE


@dataclass(frozen=True, slots=True)
class ControlPlaneArtifactLifecyclePlan:
    """Dry-run/apply-safe lifecycle plan for control-plane artifact files."""

    generated_at: datetime
    cutoff: datetime
    dry_run: bool
    artifacts: tuple[ControlPlaneArtifactRef, ...]
    resolution_issues: tuple[ControlPlaneArtifactResolutionIssue, ...] = ()

    @property
    def delete_count(self) -> int:
        """Return the number of files selected for deletion."""
        return sum(1 for artifact in self.artifacts if artifact.delete_selected)

    @property
    def retain_count(self) -> int:
        """Return the number of files retained by the planner."""
        return len(self.artifacts) - self.delete_count


@dataclass(frozen=True, slots=True)
class ControlPlaneArtifactLifecycleApplyResult:
    """Result from applying a lifecycle plan."""

    plan: ControlPlaneArtifactLifecyclePlan
    deleted_paths: tuple[str, ...]
    missing_paths: tuple[str, ...] = ()
