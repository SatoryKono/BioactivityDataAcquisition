"""Pure policy helpers for retained historical replay corpus workflows."""

from __future__ import annotations

from bioetl.domain.control_plane import RunManifest

CERTIFIED_REPLAY_KINDS = frozenset(
    {
        "historical_source_replay_certified_parent",
        "historical_composite_replay_certified_parent",
    }
)
ALREADY_REPLAYABLE_STATES = frozenset(
    {
        "exact_replay_child_run",
        "within_launch_time_snapshot_boundary",
        "within_post_capture_parent_boundary",
    }
)
ALREADY_CERTIFIED_STATES = frozenset(
    {
        "historical_source_replay_certified",
        "historical_composite_replay_certified",
    }
)
SUPPORTED_BROADER_POLICY = "certified_historical_exact_replay_tranche_supported"


def classify_certification_status(
    *,
    broader_policy: str,
    replay_occurrence_kind: str,
    broader_state: str,
) -> tuple[str, tuple[str, ...]]:
    """Classify one manifest against the supported historical replay tranche."""
    if broader_policy != SUPPORTED_BROADER_POLICY:
        return (
            "outside_certified_historical_scope",
            ("broader_historical_exact_replay_not_supported",),
        )
    if replay_occurrence_kind in CERTIFIED_REPLAY_KINDS or (
        broader_state in ALREADY_CERTIFIED_STATES
    ):
        return ("already_certified", ())
    if broader_state in ALREADY_REPLAYABLE_STATES:
        return ("already_replayable", ())
    if broader_state == "awaiting_historical_snapshot_certification":
        return (
            "awaiting_source_snapshot_certification",
            ("retained_snapshot_certification_required",),
        )
    if broader_state == "awaiting_certified_source_lineage":
        return (
            "awaiting_certified_source_lineage",
            ("certified_source_lineage_required",),
        )
    return (
        "needs_operator_review",
        ("replay_certifiability_state_requires_review",),
    )


def resolve_execution_context(manifest: RunManifest) -> str:
    """Resolve deterministic execution context from manifest fields."""
    context = str(manifest.launch_context.get("execution_context") or "").strip()
    if context:
        return context
    if manifest.provider == "composite":
        return "composite"
    return "source"


def certification_scope_for_context(execution_context: str) -> str | None:
    """Resolve certification scope for a manifest execution context."""
    if execution_context == "composite":
        return "historical_composite_replay"
    if execution_context:
        return "historical_source_replay"
    return None


def bulk_spec_order_key(manifest: RunManifest) -> tuple[int, object, str]:
    """Order source manifests before composite while keeping creation order stable."""
    execution_context = resolve_execution_context(manifest)
    source_first = 0 if execution_context != "composite" else 1
    return (source_first, manifest.created_at, manifest.manifest_id)


__all__ = [
    "bulk_spec_order_key",
    "certification_scope_for_context",
    "classify_certification_status",
    "resolve_execution_context",
]
