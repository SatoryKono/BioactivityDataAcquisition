"""Quality and structural policy bounded vocabularies for Prometheus labels."""

from __future__ import annotations

__all__ = [
    "_ALLOWED_DQ_CHECK_TYPE_LABELS",
    "_ALLOWED_DQ_DISPOSITION_LABELS",
    "_ALLOWED_STRUCTURAL_ACTION_LABELS",
    "_ALLOWED_STRUCTURAL_COMPARISON_LABELS",
]

_ALLOWED_DQ_DISPOSITION_LABELS = frozenset(
    {"pass", "warn", "quarantine", "skip", "fail", "other"}
)
_ALLOWED_DQ_CHECK_TYPE_LABELS = frozenset(
    {
        "anomaly_detection",
        "business_rules",
        "completeness",
        "content_hash_integrity",
        "data_freshness",
        "deduplication_stats",
        "encoding_validation",
        "file_integrity",
        "key_nullability",
        "null_rate",
        "raw_field_presence",
        "record_count",
        "referential_integrity",
        "schema_drift",
        "schema_snapshot",
        "scd_integrity",
        "statistical_profile",
        "type_conformance",
        "uniqueness",
        "value_distribution",
        "other",
    }
)
_ALLOWED_STRUCTURAL_ACTION_LABELS = frozenset(
    {
        "presence_quarantine",
        "required_type_quarantine",
        "nullable_type_to_null",
        "optional_nonnullable_quarantine",
        "other",
    }
)
_ALLOWED_STRUCTURAL_COMPARISON_LABELS = frozenset(
    {
        "structural_pass_silver_filter_pass",
        "structural_pass_silver_filter_reject",
        "structural_reject_silver_filter_pass",
        "structural_reject_silver_filter_reject",
        "other",
    }
)
