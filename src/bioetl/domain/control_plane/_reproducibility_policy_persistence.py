"""Required persistence-profile policy checks for reproducibility gates."""

from __future__ import annotations

from bioetl.domain.control_plane._reproducibility_policy_profiles import (
    normalize_required_persistence_profile,
)
from bioetl.domain.control_plane.run_manifest import ReplayCapability

STRICT_PERSISTENCE_PROFILES = frozenset({"replay_ready", "forensic_grade"})

__all__ = [
    "STRICT_PERSISTENCE_PROFILES",
    "archive_policy_for_persistence_profile",
    "require_input_snapshots",
    "resolve_replay_reconstructability_status",
    "validate_exact_replay_boundary",
    "validate_required_persistence_profile",
]


def archive_policy_for_persistence_profile(profile: str) -> dict[str, object] | None:
    """Return the launch-context archive policy for a persistence profile.

    `degraded_observable` never requires an off-host archive; strict
    profiles (`replay_ready`, `forensic_grade`) do. Unknown profiles yield
    no policy so archive checks stay UNKNOWN instead of guessing (#11714).
    """
    normalized = str(profile or "").strip()
    if normalized == "degraded_observable":
        return {"required": False, "policy_ref": f"persistence-profile:{normalized}"}
    if normalized in STRICT_PERSISTENCE_PROFILES:
        return {"required": True, "policy_ref": f"persistence-profile:{normalized}"}
    return None


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


def _reconstructability_verdict(
    *,
    strict_requirement: bool,
    supported: bool,
    capability_ok: bool,
) -> tuple[str, bool]:
    """Return the reconstructability status for one strictness evaluation."""
    not_ok = strict_requirement and (not supported or not capability_ok)
    if not_ok:
        return "not_reconstructable", strict_requirement
    return "reconstructable", strict_requirement


def _resolve_precomputed_reconstructability(
    *,
    replay_capability: ReplayCapability | str,
    strict_exact_replay_supported: bool,
    strict_requirement: bool,
    precomputed: dict[str, object],
) -> tuple[str, bool]:
    """Resolve the status from a cached assessment envelope."""
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
        precomputed.get("strict_exact_replay_supported", strict_exact_replay_supported)
    )
    return _reconstructability_verdict(
        strict_requirement=strict_requirement,
        supported=supported,
        capability_ok=capability_value == ReplayCapability.EXACT_REPLAY_SUPPORTED.value,
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
        return _resolve_precomputed_reconstructability(
            replay_capability=replay_capability,
            strict_exact_replay_supported=strict_exact_replay_supported,
            strict_requirement=strict_requirement,
            precomputed=precomputed,
        )
    if isinstance(replay_capability, ReplayCapability):
        capability_ok = replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
    else:
        capability_ok = (
            str(replay_capability) == ReplayCapability.EXACT_REPLAY_SUPPORTED.value
        )
    return _reconstructability_verdict(
        strict_requirement=strict_requirement,
        supported=strict_exact_replay_supported,
        capability_ok=capability_ok,
    )


def _require_manifest_for_strict_profile(
    *, profile: str, manifest_enabled: bool, execution_label: str
) -> None:
    """Require run manifests for strict persistence profiles."""
    if profile in STRICT_PERSISTENCE_PROFILES and not manifest_enabled:
        raise RuntimeError(
            f"{execution_label} requires run manifests for required persistence "
            f"profile '{profile}'; set "
            "pipeline.control_plane.run_manifest_enabled=true"
        )


def _require_exact_replay_context(
    *,
    profile: str,
    exact_replay_execution_context_supported: bool,
    execution_label: str,
) -> None:
    """Require an exact-replay-capable execution context for strict profiles."""
    if (
        profile in STRICT_PERSISTENCE_PROFILES
        and not exact_replay_execution_context_supported
    ):
        raise RuntimeError(
            f"{execution_label} cannot satisfy required persistence profile "
            f"'{profile}' because this execution context is outside the strict "
            "exact-replay support boundary"
        )


def _require_forensic_resume_evidence(
    *,
    profile: str,
    composite_resume_rich_replay_supported: bool,
    execution_label: str,
) -> None:
    """Require rich checkpoint evidence for forensic-grade replay."""
    if profile == "forensic_grade" and not composite_resume_rich_replay_supported:
        raise RuntimeError(
            f"{execution_label} cannot satisfy required persistence profile "
            f"'{profile}' because composite forensic replay requires rich "
            "checkpoint evidence that is not persisted by the current resume model"
        )


def _require_ledger_for_strict_profile(
    *, profile: str, ledger_enabled: bool, execution_label: str
) -> None:
    """Require run ledgers for strict persistence profiles."""
    if profile in STRICT_PERSISTENCE_PROFILES and not ledger_enabled:
        raise RuntimeError(
            f"{execution_label} requires run ledgers for required persistence "
            f"profile '{profile}'; set pipeline.control_plane.run_ledger_enabled=true"
        )


def _require_lineage_sidecars(
    *,
    profile: str,
    execution_label: str,
    missing_artifact_lineage_layers: tuple[str, ...],
) -> None:
    """Require metadata sidecars for strict profiles with active layers."""
    if profile in STRICT_PERSISTENCE_PROFILES and missing_artifact_lineage_layers:
        layers = ", ".join(missing_artifact_lineage_layers)
        raise RuntimeError(
            f"{execution_label} requires metadata sidecars / lineage persistence "
            f"for active layers [{layers}] to satisfy required persistence profile "
            f"'{profile}'; enable sink.<layer>.save_metadata for each active "
            "published layer"
        )


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
    _require_manifest_for_strict_profile(
        profile=profile,
        manifest_enabled=manifest_enabled,
        execution_label=execution_label,
    )
    _require_exact_replay_context(
        profile=profile,
        exact_replay_execution_context_supported=(
            exact_replay_execution_context_supported
        ),
        execution_label=execution_label,
    )
    _require_forensic_resume_evidence(
        profile=profile,
        composite_resume_rich_replay_supported=composite_resume_rich_replay_supported,
        execution_label=execution_label,
    )
    _require_ledger_for_strict_profile(
        profile=profile,
        ledger_enabled=ledger_enabled,
        execution_label=execution_label,
    )
    _require_lineage_sidecars(
        profile=profile,
        execution_label=execution_label,
        missing_artifact_lineage_layers=missing_artifact_lineage_layers,
    )
