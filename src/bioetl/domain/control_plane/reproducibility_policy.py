"""Central reproducibility policy evaluation helpers."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.control_plane._reproducibility_policy_profiles import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    is_critical_reproducibility_runtime,
    legacy_config_hash_from_resolved_config_hash,
    normalize_required_persistence_profile,
    resolve_replay_capability,
)
from bioetl.domain.control_plane._reproducibility_policy_profiles import (
    build_snapshot_envelope_status as _raw_snapshot_envelope_status,
)
from bioetl.domain.control_plane._reproducibility_policy_profiles import (
    resolve_effective_required_persistence_profile as _resolve_effective_required_persistence_profile,
)
from bioetl.domain.control_plane._reproducibility_policy_verdicts import (
    ReplayReadinessVerdict,
    resolve_replay_readiness_verdict,
)
from bioetl.domain.control_plane.run_manifest import ReplayCapability, RunSourceRef

STRICT_PERSISTENCE_PROFILES = frozenset({"replay_ready", "forensic_grade"})


@dataclass(frozen=True, slots=True)
class SnapshotEnvelopeStatus:
    """Snapshot-envelope evidence attached to one run launch."""

    source_count: int
    sources_with_snapshots: int
    any_input_snapshots: bool
    full_snapshot_envelope: bool
    require_full_snapshot_envelope: bool
    missing_snapshot_source_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReproducibilityPolicyAssessment:
    """Central verdict for replay and persistence-profile policy checks."""

    required_persistence_profile: str
    replay_capability: ReplayCapability
    strict_requirement_requested: bool
    strict_exact_replay_supported: bool
    snapshot_envelope: SnapshotEnvelopeStatus
    blocking_gaps: tuple[str, ...]
    replay_readiness_verdict: ReplayReadinessVerdict

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
            "replay_readiness_verdict": self.replay_readiness_verdict.value,
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
                "missing_snapshot_source_refs": list(
                    self.snapshot_envelope.missing_snapshot_source_refs
                ),
            },
        }


def build_snapshot_envelope_status(
    *,
    source_refs: tuple[RunSourceRef, ...],
    require_full_snapshot_envelope: bool = False,
) -> SnapshotEnvelopeStatus:
    """Return immutable snapshot evidence completeness for a run."""
    (
        source_count,
        sources_with_snapshots,
        any_input_snapshots,
        full_snapshot_envelope,
        require_full_snapshot_envelope,
    ) = _raw_snapshot_envelope_status(
        source_refs=source_refs,
        require_full_snapshot_envelope=require_full_snapshot_envelope,
    )
    missing_snapshot_source_refs = tuple(
        _source_ref_label(ref) for ref in source_refs if not ref.input_snapshots
    )
    return SnapshotEnvelopeStatus(
        source_count=source_count,
        sources_with_snapshots=sources_with_snapshots,
        any_input_snapshots=any_input_snapshots,
        full_snapshot_envelope=full_snapshot_envelope,
        require_full_snapshot_envelope=require_full_snapshot_envelope,
        missing_snapshot_source_refs=missing_snapshot_source_refs,
    )


def _source_ref_label(ref: RunSourceRef) -> str:
    """Return a stable operator-facing source-ref label."""
    provider = str(ref.provider or "").strip()
    entity = str(ref.entity or "").strip()
    pipeline_name = str(ref.pipeline_name or "").strip()
    family = ".".join(part for part in (provider, entity) if part)
    return family or pipeline_name or "unknown"


def resolve_effective_required_persistence_profile(
    *,
    configured_required_profile: object,
    family_default_profile: object,
    exact_replay_requested: bool = False,
    critical_runtime: bool = False,
) -> str:
    """Resolve the effective policy profile against the central strict set."""
    return _resolve_effective_required_persistence_profile(
        configured_required_profile=configured_required_profile,
        family_default_profile=family_default_profile,
        strict_persistence_profiles=STRICT_PERSISTENCE_PROFILES,
        exact_replay_requested=exact_replay_requested,
        critical_runtime=critical_runtime,
    )


def _resolve_blocking_gaps(
    *,
    strict_requirement_requested: bool,
    strict_exact_replay_supported: bool,
    resolved_capability: ReplayCapability,
    snapshot_envelope: SnapshotEnvelopeStatus,
) -> tuple[str, ...]:
    blocking_gaps: list[str] = []
    if strict_requirement_requested and not strict_exact_replay_supported:
        blocking_gaps.append("strict_replay_execution_context_support")
    if (
        strict_requirement_requested
        and snapshot_envelope.any_input_snapshots
        and not snapshot_envelope.full_snapshot_envelope
    ):
        blocking_gaps.append("partial_input_snapshot_envelope")
    if (
        strict_requirement_requested
        and resolved_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED
    ):
        blocking_gaps.extend(("immutable_input_snapshots", "exact_replay_capability"))
    return tuple(dict.fromkeys(blocking_gaps))


def _is_strict_requirement_requested(
    *,
    profile: str,
    exact_replay_requested: bool,
) -> bool:
    return profile in STRICT_PERSISTENCE_PROFILES or exact_replay_requested


def _resolve_effective_replay_capability(
    *,
    replay_capability: ReplayCapability | None,
    source_refs: tuple[RunSourceRef, ...],
    resume_requested: bool,
    require_full_snapshot_envelope: bool,
) -> ReplayCapability:
    if replay_capability is not None:
        return replay_capability
    return resolve_replay_capability(
        source_refs=source_refs,
        resume_requested=resume_requested,
        require_full_snapshot_envelope=require_full_snapshot_envelope,
    )


def assess_reproducibility_policy(
    *,
    source_refs: tuple[RunSourceRef, ...],
    required_persistence_profile: object,
    strict_exact_replay_supported: bool,
    exact_replay_requested: bool = False,
    resume_requested: bool = False,
    require_full_snapshot_envelope: bool = False,
    replay_capability: ReplayCapability | None = None,
    run_type: object = None,
    debug_only: bool = False,
    lifecycle_projection_only: bool = False,
) -> ReproducibilityPolicyAssessment:
    """Evaluate snapshot-envelope and profile gates in one place."""
    profile = normalize_required_persistence_profile(required_persistence_profile)
    strict_requirement_requested = _is_strict_requirement_requested(
        profile=profile,
        exact_replay_requested=exact_replay_requested,
    )
    resolved_capability = _resolve_effective_replay_capability(
        replay_capability=replay_capability,
        source_refs=source_refs,
        resume_requested=resume_requested,
        require_full_snapshot_envelope=require_full_snapshot_envelope,
    )
    snapshot_envelope = build_snapshot_envelope_status(
        source_refs=source_refs,
        require_full_snapshot_envelope=require_full_snapshot_envelope,
    )
    blocking_gaps = _resolve_blocking_gaps(
        strict_requirement_requested=strict_requirement_requested,
        strict_exact_replay_supported=strict_exact_replay_supported,
        resolved_capability=resolved_capability,
        snapshot_envelope=snapshot_envelope,
    )
    return ReproducibilityPolicyAssessment(
        required_persistence_profile=profile,
        replay_capability=resolved_capability,
        strict_requirement_requested=strict_requirement_requested,
        strict_exact_replay_supported=strict_exact_replay_supported,
        snapshot_envelope=snapshot_envelope,
        blocking_gaps=blocking_gaps,
        replay_readiness_verdict=resolve_replay_readiness_verdict(
            replay_capability=resolved_capability,
            strict_requirement_requested=strict_requirement_requested,
            strict_exact_replay_supported=strict_exact_replay_supported,
            blocking_gaps=blocking_gaps,
            exact_replay_requested=exact_replay_requested,
            resume_requested=resume_requested,
            run_type=run_type,
            debug_only=debug_only,
            lifecycle_projection_only=lifecycle_projection_only,
        ),
    )


__all__ = [
    "DEFAULT_REQUIRED_PERSISTENCE_PROFILE",
    "STRICT_PERSISTENCE_PROFILES",
    "ReplayReadinessVerdict",
    "ReproducibilityPolicyAssessment",
    "SnapshotEnvelopeStatus",
    "assess_reproducibility_policy",
    "build_snapshot_envelope_status",
    "is_critical_reproducibility_runtime",
    "legacy_config_hash_from_resolved_config_hash",
    "normalize_required_persistence_profile",
    "resolve_effective_required_persistence_profile",
    "resolve_replay_capability",
    "resolve_replay_readiness_verdict",
]
