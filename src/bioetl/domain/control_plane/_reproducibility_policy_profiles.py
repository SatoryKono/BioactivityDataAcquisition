"""Profile defaults and basic reproducibility-policy normalization helpers."""

from __future__ import annotations

from bioetl.domain.control_plane.run_manifest import ReplayCapability, RunSourceRef

DEFAULT_REQUIRED_PERSISTENCE_PROFILE = "replay_ready"


def normalize_required_persistence_profile(required_profile: object) -> str:
    """Return the canonical required persistence profile."""
    profile = (
        str(required_profile).strip()
        if required_profile is not None
        else DEFAULT_REQUIRED_PERSISTENCE_PROFILE
    )
    return profile or DEFAULT_REQUIRED_PERSISTENCE_PROFILE


def _uses_family_strict_floor(
    *,
    configured_profile: str,
    family_default_profile: str,
    strict_persistence_profiles: frozenset[str],
) -> bool:
    """Return whether the configured profile must inherit the family floor."""
    return (
        configured_profile == "degraded_observable"
        and family_default_profile in strict_persistence_profiles
    )


def _inherits_strict_family_default(
    *,
    configured_profile: str,
    family_default_profile: str,
    strict_persistence_profiles: frozenset[str],
    exact_replay_requested: bool,
    critical_runtime: bool,
) -> bool:
    """Return whether exact replay or critical runtime upgrades the profile."""
    return (
        (exact_replay_requested or critical_runtime)
        and configured_profile == DEFAULT_REQUIRED_PERSISTENCE_PROFILE
        and family_default_profile in strict_persistence_profiles
    )


def resolve_effective_required_persistence_profile(
    *,
    configured_required_profile: object,
    family_default_profile: object,
    strict_persistence_profiles: frozenset[str],
    exact_replay_requested: bool = False,
    critical_runtime: bool = False,
) -> str:
    """Resolve the effective policy profile for one run launch."""
    configured = normalize_required_persistence_profile(configured_required_profile)
    family_default = normalize_required_persistence_profile(family_default_profile)
    if _uses_family_strict_floor(
        configured_profile=configured,
        family_default_profile=family_default,
        strict_persistence_profiles=strict_persistence_profiles,
    ):
        return family_default
    if _inherits_strict_family_default(
        configured_profile=configured,
        family_default_profile=family_default,
        strict_persistence_profiles=strict_persistence_profiles,
        exact_replay_requested=exact_replay_requested,
        critical_runtime=critical_runtime,
    ):
        return family_default
    return configured


def is_critical_reproducibility_runtime(
    *,
    runtime_environment: object,
    debug_mode: object = False,
) -> bool:
    """Return whether runtime should inherit published strict family defaults."""
    return str(runtime_environment or "").strip().lower() == "prod" or bool(debug_mode)


def build_snapshot_envelope_status(
    *,
    source_refs: tuple[RunSourceRef, ...],
    require_full_snapshot_envelope: bool = False,
) -> tuple[int, int, bool, bool, bool]:
    """Return raw immutable snapshot evidence completeness for a run."""
    source_count = len(source_refs)
    sources_with_snapshots = sum(1 for ref in source_refs if ref.input_snapshots)
    return (
        source_count,
        sources_with_snapshots,
        sources_with_snapshots > 0,
        source_count > 0 and sources_with_snapshots == source_count,
        require_full_snapshot_envelope,
    )


def resolve_replay_capability(
    *,
    source_refs: tuple[RunSourceRef, ...],
    resume_requested: bool,
    require_full_snapshot_envelope: bool = False,
) -> ReplayCapability:
    """Classify exact replay capability from immutable source evidence."""
    (
        _source_count,
        _sources_with_snapshots,
        _any_input_snapshots,
        full_snapshot_envelope,
        _require_full_snapshot_envelope,
    ) = build_snapshot_envelope_status(
        source_refs=source_refs,
        require_full_snapshot_envelope=require_full_snapshot_envelope,
    )
    if full_snapshot_envelope:
        return ReplayCapability.EXACT_REPLAY_SUPPORTED
    if resume_requested:
        return ReplayCapability.RESUME_ONLY
    return ReplayCapability.REBUILD_ONLY
