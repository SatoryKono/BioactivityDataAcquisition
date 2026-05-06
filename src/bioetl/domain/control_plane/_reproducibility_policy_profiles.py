"""Profile defaults and basic reproducibility-policy normalization helpers."""

from __future__ import annotations

from bioetl.domain.control_plane.run_manifest import ReplayCapability, RunSourceRef

DEFAULT_REQUIRED_PERSISTENCE_PROFILE = "degraded_observable"


def normalize_required_persistence_profile(required_profile: object) -> str:
    """Return the canonical required persistence profile."""
    profile = (
        str(required_profile).strip()
        if required_profile is not None
        else DEFAULT_REQUIRED_PERSISTENCE_PROFILE
    )
    return profile or DEFAULT_REQUIRED_PERSISTENCE_PROFILE


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
    if (
        (exact_replay_requested or critical_runtime)
        and configured == DEFAULT_REQUIRED_PERSISTENCE_PROFILE
        and family_default in strict_persistence_profiles
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


def legacy_config_hash_from_resolved_config_hash(
    resolved_config_hash: str | None,
) -> str | None:
    """Return the documented legacy config_hash compatibility alias."""
    return resolved_config_hash


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
