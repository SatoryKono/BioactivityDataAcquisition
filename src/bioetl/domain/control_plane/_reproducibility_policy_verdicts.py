"""Replay-readiness verdict helpers for reproducibility policy."""

from __future__ import annotations

from enum import StrEnum

from bioetl.domain.control_plane.run_manifest import ReplayCapability


class ReplayReadinessVerdict(StrEnum):
    """Operator-facing replay readiness classification for one run identity."""

    EXACT_REPLAY_READY = "exact_replay_ready"
    EXACT_REPLAY_BLOCKED = "exact_replay_blocked"
    RESUME_COMPATIBLE = "resume_compatible"
    REBUILD_ONLY = "rebuild_only"
    INCREMENTAL_NEW_RUN = "incremental_new_run"
    DEBUG_ONLY = "debug_only"
    LIFECYCLE_PROJECTION_ONLY = "lifecycle_projection_only"


def _normalize_run_type_token(run_type: object) -> str:
    """Return a lowercase run-type token from enums or strings."""
    if run_type is None:
        return ""
    value = getattr(run_type, "value", run_type)
    return str(value or "").strip().lower()


def _is_exact_replay_blocked(
    *,
    replay_capability: ReplayCapability,
    strict_requirement_requested: bool,
    strict_exact_replay_supported: bool,
    blocking_gaps: tuple[str, ...],
    exact_replay_requested: bool,
) -> bool:
    return (strict_requirement_requested or exact_replay_requested) and (
        bool(blocking_gaps)
        or not strict_exact_replay_supported
        or replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED
    )


def _capability_replay_readiness_verdict(
    *,
    replay_capability: ReplayCapability,
    resume_requested: bool,
) -> ReplayReadinessVerdict | None:
    if replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED:
        return ReplayReadinessVerdict.EXACT_REPLAY_READY
    if resume_requested or replay_capability == ReplayCapability.RESUME_ONLY:
        return ReplayReadinessVerdict.RESUME_COMPATIBLE
    return None


def _fallback_replay_readiness_verdict(
    *,
    strict_exact_replay_supported: bool,
    run_type: object,
    debug_only: bool,
) -> ReplayReadinessVerdict:
    if debug_only or not strict_exact_replay_supported:
        return ReplayReadinessVerdict.DEBUG_ONLY
    if _normalize_run_type_token(run_type) == "incremental":
        return ReplayReadinessVerdict.INCREMENTAL_NEW_RUN
    return ReplayReadinessVerdict.REBUILD_ONLY


def resolve_replay_readiness_verdict(
    *,
    replay_capability: ReplayCapability,
    strict_requirement_requested: bool,
    strict_exact_replay_supported: bool,
    blocking_gaps: tuple[str, ...] = (),
    exact_replay_requested: bool = False,
    resume_requested: bool = False,
    run_type: object = None,
    debug_only: bool = False,
    lifecycle_projection_only: bool = False,
) -> ReplayReadinessVerdict:
    """Classify replay/resume/rebuild readiness without conflating modes."""
    if lifecycle_projection_only:
        return ReplayReadinessVerdict.LIFECYCLE_PROJECTION_ONLY
    if _is_exact_replay_blocked(
        replay_capability=replay_capability,
        strict_requirement_requested=strict_requirement_requested,
        strict_exact_replay_supported=strict_exact_replay_supported,
        blocking_gaps=blocking_gaps,
        exact_replay_requested=exact_replay_requested,
    ):
        return ReplayReadinessVerdict.EXACT_REPLAY_BLOCKED
    capability_verdict = _capability_replay_readiness_verdict(
        replay_capability=replay_capability,
        resume_requested=resume_requested,
    )
    if capability_verdict is not None:
        return capability_verdict
    return _fallback_replay_readiness_verdict(
        strict_exact_replay_supported=strict_exact_replay_supported,
        run_type=run_type,
        debug_only=debug_only,
    )
