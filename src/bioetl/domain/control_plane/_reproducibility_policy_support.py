"""Private support helpers for reproducibility policy evaluation."""

from __future__ import annotations

from bioetl.domain.control_plane.run_manifest import ReplayCapability, RunSourceRef


def missing_snapshot_source_labels(source_refs: tuple[RunSourceRef, ...]) -> tuple[str, ...]:
    """Return stable operator-facing labels for sources missing snapshots."""
    return tuple(_source_ref_label(ref) for ref in source_refs if not ref.input_snapshots)


def resolve_blocking_gaps(
    *,
    strict_requirement_requested: bool,
    strict_exact_replay_supported: bool,
    resolved_capability: ReplayCapability,
    any_input_snapshots: bool,
    full_snapshot_envelope: bool,
) -> tuple[str, ...]:
    """Return de-duplicated blocking gaps for the current reproducibility state."""
    blocking_gaps: list[str] = []
    if strict_requirement_requested and not strict_exact_replay_supported:
        blocking_gaps.append("strict_replay_execution_context_support")
    if (
        strict_requirement_requested
        and any_input_snapshots
        and not full_snapshot_envelope
    ):
        blocking_gaps.append("partial_input_snapshot_envelope")
    if (
        strict_requirement_requested
        and resolved_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED
    ):
        blocking_gaps.extend(("immutable_input_snapshots", "exact_replay_capability"))
    return tuple(dict.fromkeys(blocking_gaps))


def is_strict_requirement_requested(
    *,
    profile: str,
    strict_persistence_profiles: frozenset[str],
    exact_replay_requested: bool,
) -> bool:
    """Return whether strict reproducibility guarantees are required."""
    return profile in strict_persistence_profiles or exact_replay_requested


def resolve_effective_replay_capability(
    *,
    replay_capability: ReplayCapability | None,
    source_refs: tuple[RunSourceRef, ...],
    resume_requested: bool,
    require_full_snapshot_envelope: bool,
    replay_capability_resolver: callable,
) -> ReplayCapability:
    """Return explicit capability override or derive one from source evidence."""
    if replay_capability is not None:
        return replay_capability
    return replay_capability_resolver(
        source_refs=source_refs,
        resume_requested=resume_requested,
        require_full_snapshot_envelope=require_full_snapshot_envelope,
    )


def _source_ref_label(ref: RunSourceRef) -> str:
    """Return a stable operator-facing source-ref label."""
    family = _source_ref_family_label(ref)
    if family is not None:
        return family
    return _normalized_source_ref_value(ref.pipeline_name) or "unknown"


def _normalized_source_ref_value(value: object) -> str:
    return str(value or "").strip()


def _source_ref_family_label(ref: RunSourceRef) -> str | None:
    family_parts = tuple(
        part
        for part in (
            _normalized_source_ref_value(ref.provider),
            _normalized_source_ref_value(ref.entity),
        )
        if part
    )
    if not family_parts:
        return None
    return ".".join(family_parts)
