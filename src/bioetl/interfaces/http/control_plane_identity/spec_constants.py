"""Shared Control Plane identity spec constants."""

from __future__ import annotations

TERMINAL_STATUSES = frozenset({"success", "failed", "shutdown"})
CHECKPOINT_ANCHORS = (
    "manifest_id",
    "execution_fingerprint",
    "effective_config_hash",
    "effective_config_artifact_id",
    "input_snapshot_fingerprint",
    "composite_run_identity",
)
ALLOWED_LOW_CARDINALITY_LABELS = [
    "pipeline",
    "run_type",
    "status",
    "layer",
    "event_type",
    "disposition",
    "ref_type",
    "decision_type",
    "selected_source",
]

__all__ = [
    "ALLOWED_LOW_CARDINALITY_LABELS",
    "CHECKPOINT_ANCHORS",
    "TERMINAL_STATUSES",
]
