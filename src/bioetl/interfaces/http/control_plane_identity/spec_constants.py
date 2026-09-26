"""Shared Control Plane identity spec constants."""

from __future__ import annotations

ANCHOR_SPEC_VERSION = "1.0.0"
SPEC_VALIDATION_RULES = (
    "anchor_name_required",
    "display_name_required",
    "priority_required",
    "source_location_required",
)
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
    "ANCHOR_SPEC_VERSION",
    "CHECKPOINT_ANCHORS",
    "SPEC_VALIDATION_RULES",
    "TERMINAL_STATUSES",
]
