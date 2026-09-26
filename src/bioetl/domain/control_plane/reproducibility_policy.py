"""Central reproducibility policy evaluation helpers."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.control_plane._reproducibility_policy_profiles import (
    DEFAULT_REQUIRED_PERSISTENCE_PROFILE,
    is_critical_reproducibility_runtime,
    normalize_required_persistence_profile,
    resolve_replay_capability,
)
from bioetl.domain.control_plane._reproducibility_policy_profiles import (
    build_snapshot_envelope_status as _raw_snapshot_envelope_status,
)
from bioetl.domain.control_plane._reproducibility_policy_profiles import (
    resolve_effective_required_persistence_profile as _resolve_effective_required_persistence_profile,
)
from bioetl.domain.control_plane._reproducibility_policy_support import (
    is_strict_requirement_requested,
    missing_snapshot_source_labels,
    resolve_blocking_gaps,
    resolve_effective_replay_capability,
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
    missing_snapshot_source_refs = missing_snapshot_source_labels(source_refs)
    return SnapshotEnvelopeStatus(
        source_count=source_count,
        sources_with_snapshots=sources_with_snapshots,
        any_input_snapshots=any_input_snapshots,
        full_snapshot_envelope=full_snapshot_envelope,
        require_full_snapshot_envelope=require_full_snapshot_envelope,
        missing_snapshot_source_refs=missing_snapshot_source_refs,
    )


def resolve_effective_required_persistence_profile(
    *,
    configured_required_profile: object,
    family_default_profile: object,
    strict_persistence_profiles: frozenset[str] | None = None,
    exact_replay_requested: bool = False,
    critical_runtime: bool = False,
    allow_degraded_opt_down: bool = False,
) -> str:
    """Resolve the effective policy profile against the central strict set."""
    return _resolve_effective_required_persistence_profile(
        configured_required_profile=configured_required_profile,
        family_default_profile=family_default_profile,
        strict_persistence_profiles=(
            strict_persistence_profiles or STRICT_PERSISTENCE_PROFILES
        ),
        exact_replay_requested=exact_replay_requested,
        critical_runtime=critical_runtime,
        allow_degraded_opt_down=allow_degraded_opt_down,
    )


def is_degraded_observable_profile_requested(
    required_persistence_profile: object,
) -> bool:
    """Return whether a launch explicitly requested the local degraded floor."""
    if required_persistence_profile is None:
        return False
    profile_text = str(required_persistence_profile).strip()
    if not profile_text:
        return False
    return normalize_required_persistence_profile(profile_text) == "degraded_observable"


def is_degraded_opt_down_eligible(
    *,
    opt_down_requested: bool,
    configured_required_profile: object,
    exact_replay_requested: bool,
    critical_runtime: bool,
) -> bool:
    """Return whether a launch may opt down to the degraded_observable floor.

    Eligibility requires an explicit opt-down flag, a degraded_observable
    configured profile, no exact-replay request, and a non-critical runtime.
    """
    return (
        bool(opt_down_requested)
        and is_degraded_observable_profile_requested(configured_required_profile)
        and not bool(exact_replay_requested)
        and not bool(critical_runtime)
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
    strict_requirement_requested = is_strict_requirement_requested(
        profile=profile,
        strict_persistence_profiles=STRICT_PERSISTENCE_PROFILES,
        exact_replay_requested=exact_replay_requested,
    )
    resolved_capability = resolve_effective_replay_capability(
        replay_capability=replay_capability,
        source_refs=source_refs,
        resume_requested=resume_requested,
        require_full_snapshot_envelope=require_full_snapshot_envelope,
        replay_capability_resolver=resolve_replay_capability,
    )
    snapshot_envelope = build_snapshot_envelope_status(
        source_refs=source_refs,
        require_full_snapshot_envelope=require_full_snapshot_envelope,
    )
    blocking_gaps = resolve_blocking_gaps(
        strict_requirement_requested=strict_requirement_requested,
        strict_exact_replay_supported=strict_exact_replay_supported,
        resolved_capability=resolved_capability,
        any_input_snapshots=snapshot_envelope.any_input_snapshots,
        full_snapshot_envelope=snapshot_envelope.full_snapshot_envelope,
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


def require_input_snapshots(
    *,
    exact_replay: bool,
    required_persistence_profile: object,
    input_snapshots: tuple[object, ...] | list[object],
) -> None:
    """Fail closed when strict profiles lack immutable input snapshots (#11226)."""
    required_profile = normalize_required_persistence_profile(
        required_persistence_profile
    )
    strict_snapshot_required = bool(exact_replay) or (
        required_profile in STRICT_PERSISTENCE_PROFILES
    )
    if strict_snapshot_required and not input_snapshots:
        raise RuntimeError(
            "Exact replay and strict persistence profiles require immutable "
            "input snapshots; no snapshot-backed source refs were resolved "
            f"for required persistence profile '{required_profile}'"
        )


def validate_exact_replay_boundary(
    *,
    exact_replay: bool,
    strict_exact_replay_supported: bool,
) -> None:
    """Reject exact replay outside the published support boundary (#11226)."""
    if not exact_replay:
        return
    if strict_exact_replay_supported:
        return
    raise RuntimeError(
        "Pipeline execution is outside the published strict exact-replay "
        "support boundary for this run family"
    )


def resolve_replay_reconstructability_status(
    *,
    replay_capability: ReplayCapability | str,
    strict_exact_replay_supported: bool,
    strict_requirement: bool,
    precomputed: dict[str, object] | None = None,
) -> tuple[str, bool]:
    """Return ``(status, effective_strict_requirement)`` for manifest metrics."""
    if precomputed is not None:
        strict_requirement = bool(
            precomputed.get("strict_requirement_requested", strict_requirement)
        )
        assessment_capability = precomputed.get("replay_capability")
        if isinstance(assessment_capability, str):
            capability_value = assessment_capability
        elif isinstance(replay_capability, ReplayCapability):
            capability_value = replay_capability.value
        else:
            capability_value = str(replay_capability)
        supported = bool(
            precomputed.get(
                "strict_exact_replay_supported", strict_exact_replay_supported
            )
        )
        not_ok = strict_requirement and (
            not supported
            or capability_value != ReplayCapability.EXACT_REPLAY_SUPPORTED.value
        )
        return (
            "not_reconstructable" if not_ok else "reconstructable",
            strict_requirement,
        )
    capability_ok = (
        replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
        if isinstance(replay_capability, ReplayCapability)
        else str(replay_capability) == ReplayCapability.EXACT_REPLAY_SUPPORTED.value
    )
    not_ok = strict_requirement and (
        not strict_exact_replay_supported or not capability_ok
    )
    return ("not_reconstructable" if not_ok else "reconstructable", strict_requirement)


def validate_required_persistence_profile(
    *,
    manifest_enabled: bool,
    ledger_enabled: bool,
    required_profile: object,
    execution_label: str,
    exact_replay_execution_context_supported: bool = True,
    composite_resume_rich_replay_supported: bool = True,
    missing_artifact_lineage_layers: tuple[str, ...] = (),
) -> None:
    """Fail closed when static control-plane flags cannot satisfy required profile."""
    profile = normalize_required_persistence_profile(required_profile)
    if profile in STRICT_PERSISTENCE_PROFILES and not manifest_enabled:
        raise RuntimeError(
            f"{execution_label} requires run manifests for required persistence "
            f"profile '{profile}'; set "
            "pipeline.control_plane.run_manifest_enabled=true"
        )
    if (
        profile in STRICT_PERSISTENCE_PROFILES
        and not exact_replay_execution_context_supported
    ):
        raise RuntimeError(
            f"{execution_label} cannot satisfy required persistence profile "
            f"'{profile}' because this execution context is outside the strict "
            "exact-replay support boundary"
        )
    if profile == "forensic_grade" and not composite_resume_rich_replay_supported:
        raise RuntimeError(
            f"{execution_label} cannot satisfy required persistence profile "
            f"'{profile}' because composite forensic replay requires rich "
            "checkpoint evidence that is not persisted by the current resume model"
        )
    if profile in STRICT_PERSISTENCE_PROFILES and not ledger_enabled:
        raise RuntimeError(
            f"{execution_label} requires run ledgers for required persistence "
            f"profile '{profile}'; set pipeline.control_plane.run_ledger_enabled=true"
        )
    if profile in STRICT_PERSISTENCE_PROFILES and missing_artifact_lineage_layers:
        layers = ", ".join(missing_artifact_lineage_layers)
        raise RuntimeError(
            f"{execution_label} requires metadata sidecars / lineage persistence "
            f"for active layers [{layers}] to satisfy required persistence profile "
            f"'{profile}'; enable sink.<layer>.save_metadata for each active "
            "published layer"
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
    "is_degraded_observable_profile_requested",
    "is_degraded_opt_down_eligible",
    "normalize_required_persistence_profile",
    "require_input_snapshots",
    "resolve_effective_required_persistence_profile",
    "resolve_replay_capability",
    "resolve_replay_readiness_verdict",
    "resolve_replay_reconstructability_status",
    "validate_exact_replay_boundary",
    "validate_required_persistence_profile",
]
