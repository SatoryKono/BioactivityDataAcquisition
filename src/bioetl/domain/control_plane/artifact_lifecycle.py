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
