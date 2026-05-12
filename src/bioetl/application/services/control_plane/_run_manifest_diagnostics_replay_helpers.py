"""Helper functions for replay diagnostics.

Extracted from _run_manifest_diagnostics_replay.py to meet file size limits.
"""

from __future__ import annotations

from bioetl.application.services.control_plane._historical_replay_certification import (
    HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED,
    HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED,
    LIVE_CAPTURE_SNAPSHOT_MATERIALIZED,
)
from bioetl.domain.control_plane import ReplayCapability, RunManifest
from bioetl.domain.control_plane.reproducibility_policy import (
    ReproducibilityPolicyAssessment,
)


def _has_partial_input_snapshot_envelope(snapshot_envelope: object) -> bool:
    any_snapshots = bool(getattr(snapshot_envelope, "any_input_snapshots", False))
    full_envelope = bool(getattr(snapshot_envelope, "full_snapshot_envelope", False))
    return any_snapshots and not full_envelope


def _resolve_exact_replay_supported_reason(
    *,
    manifest: RunManifest,
    input_snapshots: list[dict[str, object]],
    snapshot_envelope: object,
) -> str | None:
    if manifest.replay_capability != ReplayCapability.EXACT_REPLAY_SUPPORTED:
        return None
    if not bool(getattr(snapshot_envelope, "full_snapshot_envelope", False)):
        return None
    if _has_live_capture_materialized_snapshots(input_snapshots):
        return "materialized_live_capture_snapshot_envelope_present"
    return "full_immutable_input_snapshot_envelope_present"


def _requires_resume_without_snapshot_reason(
    *,
    manifest: RunManifest,
    resume_requested: bool,
) -> bool:
    return (
        manifest.replay_capability == ReplayCapability.RESUME_ONLY or resume_requested
    )


def _has_historical_composite_certified_snapshots(
    input_snapshots: list[dict[str, object]],
) -> bool:
    return any(
        snapshot.get("certification") == HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED
        for snapshot in input_snapshots
    )


def _has_historical_source_certified_snapshots(
    input_snapshots: list[dict[str, object]],
) -> bool:
    return any(
        snapshot.get("certification") == HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED
        for snapshot in input_snapshots
    )


def _has_live_capture_materialized_snapshots(
    input_snapshots: list[dict[str, object]],
) -> bool:
    return any(
        snapshot.get("certification") == LIVE_CAPTURE_SNAPSHOT_MATERIALIZED
        for snapshot in input_snapshots
    )


def _is_full_scan_idempotent_rebuild(manifest: RunManifest) -> bool:
    return manifest.launch_context.get("full_scan_idempotent_rebuild", False)


def _is_composite_execution_context(manifest: RunManifest) -> bool:
    return manifest.launch_context.get("execution_context") == "composite"


def _collect_append_mode_semantic_sinks(manifest: RunManifest) -> list[str]:
    sinks = manifest.launch_context.get("append_mode_semantic_sinks")
    return sinks if isinstance(sinks, list) else []


__all__ = [
    "_has_partial_input_snapshot_envelope",
    "_resolve_exact_replay_supported_reason",
    "_requires_resume_without_snapshot_reason",
    "_has_historical_composite_certified_snapshots",
    "_has_historical_source_certified_snapshots",
    "_has_live_capture_materialized_snapshots",
    "_is_full_scan_idempotent_rebuild",
    "_is_composite_execution_context",
    "_collect_append_mode_semantic_sinks",
]
