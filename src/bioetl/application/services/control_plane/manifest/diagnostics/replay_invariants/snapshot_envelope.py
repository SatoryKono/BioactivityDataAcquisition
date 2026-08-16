"""Snapshot-envelope invariants for replay diagnostics."""

from __future__ import annotations

from bioetl.application.services.control_plane.replay.historical_certification import (
    HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED,
    HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED,
)
from bioetl.application.services.control_plane.replay.historical_certification import (
    LIVE_CAPTURE_SNAPSHOT_MATERIALIZED as LIVE_CAPTURE_SNAPSHOT_MATERIALIZED,
)
from bioetl.domain.control_plane import ReplayCapability, RunManifest

_LIVE_CAPTURE_SNAPSHOT_MATERIALIZED = "live_capture_snapshot_materialized"


def _has_partial_input_snapshot_envelope(snapshot_envelope: object) -> bool:
    any_snapshots = bool(getattr(snapshot_envelope, "any_input_snapshots", False))
    full_envelope = bool(getattr(snapshot_envelope, "full_snapshot_envelope", False))
    return any_snapshots and not full_envelope


def _resolve_snapshot_materialization_mode(snapshot: dict[str, object]) -> str | None:
    """Read the canonical snapshot promotion/materialization marker."""
    for field_name in ("materialization_mode", "certification"):
        value = snapshot.get(field_name)
        text = str(value or "").strip()
        if text:
            return text
    return None


def _has_historical_composite_certified_snapshots(
    input_snapshots: list[dict[str, object]],
) -> bool:
    return any(
        _resolve_snapshot_materialization_mode(snapshot)
        == HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED
        for snapshot in input_snapshots
    )


def _has_historical_source_certified_snapshots(
    input_snapshots: list[dict[str, object]],
) -> bool:
    return any(
        _resolve_snapshot_materialization_mode(snapshot)
        == HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED
        for snapshot in input_snapshots
    )


def _has_live_capture_materialized_snapshots(
    input_snapshots: list[dict[str, object]],
) -> bool:
    return any(
        _resolve_snapshot_materialization_mode(snapshot)
        == _LIVE_CAPTURE_SNAPSHOT_MATERIALIZED
        for snapshot in input_snapshots
    )


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


__all__ = [
    "_has_historical_composite_certified_snapshots",
    "_has_historical_source_certified_snapshots",
    "_has_live_capture_materialized_snapshots",
    "_has_partial_input_snapshot_envelope",
    "_resolve_exact_replay_supported_reason",
    "_resolve_snapshot_materialization_mode",
]
