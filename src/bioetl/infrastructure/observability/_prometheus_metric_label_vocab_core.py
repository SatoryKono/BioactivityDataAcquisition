"""Core bounded vocabularies for Prometheus metric label normalizers."""

from __future__ import annotations

__all__ = [
    "_ALLOWED_FILTER_SOURCE_KIND_LABELS",
    "_ALLOWED_FLOW_STAGE_LABELS",
    "_ALLOWED_REASON_LABELS",
    "_ALLOWED_RECORD_FLOW_INVARIANT_LABELS",
    "_ALLOWED_RECORD_FLOW_INVARIANT_STATUS_LABELS",
    "_ALLOWED_RUNTIME_STAGE_LABELS",
    "_ALLOWED_SEVERITY_LABELS",
    "_ALLOWED_STAGE_LABELS",
    "_ALLOWED_TERMINAL_STATUS_LABELS",
]

_ALLOWED_REASON_LABELS = frozenset(
    {
        "cross_validation",
        "filtered_out_silver",
        "data_quality",
        "schema_validation",
        "transform_error",
        "validation_error",
        "other",
    }
)
_ALLOWED_FILTER_SOURCE_KIND_LABELS = frozenset(
    {
        "csv_single_column",
        "csv_multi_column",
        "direct_ids",
        "direct_multi_ids",
        "other",
    }
)
_ALLOWED_STAGE_LABELS = frozenset(
    {
        "validation",
        "threshold",
        "transform",
        "bronze",
        "silver",
        "gold",
        "postrun",
        "other",
    }
)
_ALLOWED_RUNTIME_STAGE_LABELS = frozenset(
    {
        "pipeline",
        "startup",
        "preflight",
        "lifecycle_clear",
        "execution",
        "postrun",
        "cleanup",
        "bronze",
        "silver",
        "gold",
        "filtered_out",
        "quarantined",
        "transform",
        "validation",
        "write",
        "checkpoint",
        "extract",
        "load",
        "other",
    }
)
_ALLOWED_FLOW_STAGE_LABELS = frozenset(
    {
        "fetched",
        "bronze",
        "silver",
        "gold",
        "filtered_out",
        "quarantined",
        "other",
    }
)
_ALLOWED_RECORD_FLOW_INVARIANT_LABELS = frozenset(
    {
        "fetched_equals_bronze",
        "bronze_partitioned",
        "silver_gold_monotonic",
        "other",
    }
)
_ALLOWED_RECORD_FLOW_INVARIANT_STATUS_LABELS = frozenset(
    {"passed", "violated", "unknown", "other"}
)
_ALLOWED_SEVERITY_LABELS = frozenset(
    {"soft_fail", "hard_fail", "warning", "error", "other"}
)
_ALLOWED_TERMINAL_STATUS_LABELS = frozenset({"success", "failed", "shutdown", "other"})
