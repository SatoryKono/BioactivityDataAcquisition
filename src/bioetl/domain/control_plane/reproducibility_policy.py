"""Central reproducibility policy evaluation helpers."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.control_plane.run_manifest import ReplayCapability, RunSourceRef

DEFAULT_REQUIRED_PERSISTENCE_PROFILE = "degraded_observable"
STRICT_PERSISTENCE_PROFILES = frozenset({"replay_ready", "forensic_grade"})


@dataclass(frozen=True, slots=True)
class SnapshotEnvelopeStatus:
    """Snapshot-envelope evidence attached to one run launch."""

    source_count: int
    sources_with_snapshots: int
    any_input_snapshots: bool
    full_snapshot_envelope: bool
    require_full_snapshot_envelope: bool


@dataclass(frozen=True, slots=True)
class ReproducibilityPolicyAssessment:
    """Central verdict for replay and persistence-profile policy checks."""

    required_persistence_profile: str
    replay_capability: ReplayCapability
    strict_requirement_requested: bool
    strict_exact_replay_supported: bool
    snapshot_envelope: SnapshotEnvelopeStatus
    blocking_gaps: tuple[str, ...]

    @property
    def required_profile_satisfied(self) -> bool:
        """Return whether strict policy requirements are currently satisfied."""
        return not self.blocking_gaps

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe diagnostics payload."""
        return {
            "required_persistence_profile": self.required_persistence_profile,
            "replay_capability": self.replay_capability.value,
            "strict_requirement_requested": self.strict_requirement_requested,
            "strict_exact_replay_supported": self.strict_exact_replay_supported,
            "required_profile_satisfied": self.required_profile_satisfied,
            "blocking_gaps": list(self.blocking_gaps),
            "snapshot_envelope": {
                "source_count": self.snapshot_envelope.source_count,
                "sources_with_snapshots": (
                    self.snapshot_envelope.sources_with_snapshots
                ),
                "any_input_snapshots": self.snapshot_envelope.any_input_snapshots,
                "full_snapshot_envelope": (
                    self.snapshot_envelope.full_snapshot_envelope
                ),
                "require_full_snapshot_envelope": (
                    self.snapshot_envelope.require_full_snapshot_envelope
                ),
            },
        }


def normalize_required_persistence_profile(required_profile: object) -> str:
    """Return the canonical required persistence profile."""
    profile = (
        str(required_profile).strip()
        if required_profile is not None
        else DEFAULT_REQUIRED_PERSISTENCE_PROFILE
    )
    return profile or DEFAULT_REQUIRED_PERSISTENCE_PROFILE


def build_snapshot_envelope_status(
    *,
    source_refs: tuple[RunSourceRef, ...],
    require_full_snapshot_envelope: bool = False,
) -> SnapshotEnvelopeStatus:
    """Return immutable snapshot evidence completeness for a run."""
    source_count = len(source_refs)
    sources_with_snapshots = sum(1 for ref in source_refs if ref.input_snapshots)
    return SnapshotEnvelopeStatus(
        source_count=source_count,
        sources_with_snapshots=sources_with_snapshots,
        any_input_snapshots=sources_with_snapshots > 0,
        full_snapshot_envelope=source_count > 0
        and sources_with_snapshots == source_count,
        require_full_snapshot_envelope=require_full_snapshot_envelope,
    )


def resolve_replay_capability(
    *,
    source_refs: tuple[RunSourceRef, ...],
    resume_requested: bool,
    require_full_snapshot_envelope: bool = False,
) -> ReplayCapability:
    """Classify exact replay capability from immutable source evidence."""
    snapshot_envelope = build_snapshot_envelope_status(
        source_refs=source_refs,
        require_full_snapshot_envelope=require_full_snapshot_envelope,
    )
    exact_supported = (
        snapshot_envelope.full_snapshot_envelope
        if require_full_snapshot_envelope
        else snapshot_envelope.any_input_snapshots
    )
    if exact_supported:
        return ReplayCapability.EXACT_REPLAY_SUPPORTED
    if resume_requested:
        return ReplayCapability.RESUME_ONLY
    return ReplayCapability.REBUILD_ONLY


def assess_reproducibility_policy(
    *,
    source_refs: tuple[RunSourceRef, ...],
    required_persistence_profile: object,
    strict_exact_replay_supported: bool,
    exact_replay_requested: bool = False,
    resume_requested: bool = False,
    require_full_snapshot_envelope: bool = False,
    replay_capability: ReplayCapability | None = None,
) -> ReproducibilityPolicyAssessment:
    """Evaluate snapshot-envelope and profile gates in one place."""
    profile = normalize_required_persistence_profile(required_persistence_profile)
    strict_requirement_requested = (
        profile in STRICT_PERSISTENCE_PROFILES or exact_replay_requested
    )
    resolved_capability = replay_capability or resolve_replay_capability(
        source_refs=source_refs,
        resume_requested=resume_requested,
        require_full_snapshot_envelope=require_full_snapshot_envelope,
    )
    snapshot_envelope = build_snapshot_envelope_status(
        source_refs=source_refs,
        require_full_snapshot_envelope=require_full_snapshot_envelope,
    )
    blocking_gaps: list[str] = []
    if strict_requirement_requested and not strict_exact_replay_supported:
        blocking_gaps.append("strict_replay_execution_context_support")
    if (
        strict_requirement_requested
        and resolved_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED
    ):
        blocking_gaps.append("immutable_input_snapshots")
        blocking_gaps.append("exact_replay_capability")
    return ReproducibilityPolicyAssessment(
        required_persistence_profile=profile,
        replay_capability=resolved_capability,
        strict_requirement_requested=strict_requirement_requested,
        strict_exact_replay_supported=strict_exact_replay_supported,
        snapshot_envelope=snapshot_envelope,
        blocking_gaps=tuple(dict.fromkeys(blocking_gaps)),
    )


__all__ = [
    "DEFAULT_REQUIRED_PERSISTENCE_PROFILE",
    "STRICT_PERSISTENCE_PROFILES",
    "ReproducibilityPolicyAssessment",
    "SnapshotEnvelopeStatus",
    "assess_reproducibility_policy",
    "build_snapshot_envelope_status",
    "normalize_required_persistence_profile",
    "resolve_replay_capability",
]
