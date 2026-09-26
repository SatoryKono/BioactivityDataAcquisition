"""Enum definitions for Data Quality reports."""

from __future__ import annotations

from enum import StrEnum


class DQReportFormat(StrEnum):
    """Output format for DQ reports."""

    JSON = "json"
    YAML = "yaml"
    HTML = "html"


class DQCheckStatus(StrEnum):
    """Status of individual DQ check."""

    PASS = "pass"  # nosec B105
    WARN = "warn"
    FAIL = "fail"


class DQReportStatus(StrEnum):
    """Overall status of DQ report."""

    PASS = "pass"  # nosec B105
    WARNING = "warning"
    FAIL = "fail"


# =============================================================================
# Bronze DQ Check Types
# =============================================================================


class BronzeDQCheckType(StrEnum):
    """Types of DQ checks for Bronze layer."""

    RECORD_COUNT = "record_count"
    FILE_INTEGRITY = "file_integrity"
    SCHEMA_SNAPSHOT = "schema_snapshot"
    RAW_FIELD_PRESENCE = "raw_field_presence"
    ENCODING_VALIDATION = "encoding_validation"


# =============================================================================
# Silver DQ Check Types
# =============================================================================


class SilverDQCheckType(StrEnum):
    """Types of DQ checks for Silver layer."""

    RECORD_COUNT = "record_count"
    NULL_RATE = "null_rate"
    UNIQUENESS = "uniqueness"
    TYPE_CONFORMANCE = "type_conformance"
    VALUE_DISTRIBUTION = "value_distribution"
    SCHEMA_DRIFT = "schema_drift"
    DEDUPLICATION_STATS = "deduplication_stats"
    CONTENT_HASH_INTEGRITY = "content_hash_integrity"
    KEY_NULLABILITY = "key_nullability"


# =============================================================================
# Gold DQ Check Types
# =============================================================================


class GoldDQCheckType(StrEnum):
    """Types of DQ checks for Gold layer."""

    RECORD_COUNT = "record_count"
    COMPLETENESS = "completeness"
    BUSINESS_RULES = "business_rules"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    STATISTICAL_PROFILE = "statistical_profile"
    ANOMALY_DETECTION = "anomaly_detection"
    SCD_INTEGRITY = "scd_integrity"


__all__ = [
    "BronzeDQCheckType",
    "DQCheckStatus",
    "DQReportFormat",
    "DQReportStatus",
    "GoldDQCheckType",
    "SilverDQCheckType",
]
