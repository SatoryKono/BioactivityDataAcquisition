"""Pure domain transformations (no I/O).

Implements RULES.md §2.8 - Entity ID Generation and Content Hashing.

Requirements:
- REQ-ARCH-003: No I/O in domain layer
- REQ-ID-001 to REQ-ID-008: Content hash algorithm
- REQ-SCHEMA-001 to REQ-SCHEMA-004: Schema drift detection

All functions are pure (deterministic, side-effect free).
"""

import hashlib
import json
import math
from datetime import date, datetime
from functools import singledispatch
from typing import Any

from .types import ContentHash, DriftLevel, EntityID

# =============================================================================
# Content Hash Generation (RULES.md §2.8)
# =============================================================================

# Meta-fields to exclude from hash calculation
META_FIELDS = {
    "_ingestion_ts",
    "_run_id",
    "_run_type",
    "_dq_warn",
    "_dq_error",
    "_source_batch_id",
}


@singledispatch
def _normalize_value(value: Any) -> Any:
    """Normalize a single value using singledispatch."""
    return value


@_normalize_value.register(float)
def _normalize_float(value: float) -> float | None:
    """Normalize a float value, handling NaN/Inf."""
    if math.isnan(value) or math.isinf(value):
        return None
    return round(value, 10)


@_normalize_value.register(datetime)
def _normalize_datetime(value: datetime) -> str:
    """Normalize datetime to date ISO string."""
    return value.date().isoformat()


@_normalize_value.register(date)
def _normalize_date(value: date) -> str:
    """Normalize date to ISO string."""
    return value.isoformat()


@_normalize_value.register(str)
def _normalize_str(value: str) -> str:
    """Normalize string by stripping whitespace."""
    return value.strip()


@_normalize_value.register(dict)
def _normalize_dict(value: dict[str, Any]) -> dict[str, Any]:
    """Normalize dict by recursively normalizing values."""
    return {k: _normalize_value(v) for k, v in value.items()}


@_normalize_value.register(list)
def _normalize_list(value: list[Any]) -> list[Any]:
    """Normalize list by recursively normalizing elements."""
    return [_normalize_value(v) for v in value]


def _should_include_field(key: str, value: Any, exclude_none: bool) -> bool:
    """Check if field should be included in hash calculation."""
    if key in META_FIELDS:
        return False
    return not (exclude_none and value is None)


def normalize_for_hash(record: dict[str, Any], exclude_none: bool = False) -> dict[str, Any]:
    """Normalize record before hashing to ensure consistency."""
    return {
        key: _normalize_value(value)
        for key, value in record.items()
        if _should_include_field(key, value, exclude_none)
    }


def canonical_json_dumps(obj: dict[str, Any]) -> str:
    """Convert object to canonical JSON representation."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def generate_content_hash(
    record: dict[str, Any], provider: str, exclude_none: bool = False
) -> ContentHash:
    """Generate SHA256 content hash for record versioning."""
    normalized = normalize_for_hash(record, exclude_none=exclude_none)
    canonical = canonical_json_dumps(normalized)
    data = f"{provider}{canonical}"
    hash_digest = hashlib.sha256(data.encode("utf-8")).hexdigest()
    return ContentHash(hash_digest)


def generate_entity_id(
    record: dict[str, Any],
    provider: str,
    id_field: str | None = None,
) -> EntityID:
    """Generate stable entity ID (business key)."""
    if id_field and id_field in record:
        stable_id = str(record[id_field])
        return EntityID(f"{provider}:{stable_id}")
    content_hash = generate_content_hash(record, provider)
    return EntityID(f"{provider}:{content_hash[:16]}")


# =============================================================================
# Schema Drift Detection (RULES.md §2.2)
# =============================================================================


def detect_schema_drift(
    old_schema: set[str],
    new_schema: set[str],
    required_fields: set[str] | None = None,
) -> tuple[DriftLevel, dict[str, Any]]:
    """Detect schema drift between two schemas."""
    added = sorted(new_schema - old_schema)
    removed = sorted(old_schema - new_schema)
    missing_required = sorted((required_fields or set()) & set(removed))

    level = DriftLevel.INFO
    if missing_required:
        level = DriftLevel.CRITICAL
    elif len(added) > 3:
        level = DriftLevel.WARN

    details = {
        "added_fields": added,
        "removed_fields": removed,
        "field_count_delta": len(added) - len(removed),
    }
    if missing_required:
        details["missing_required"] = missing_required

    return level, details


# =============================================================================
# Data Quality Helpers
# =============================================================================


def calculate_dq_score(valid_count: int, total_count: int) -> float:
    """Calculate data quality score (0.0 to 1.0)."""
    if total_count == 0:
        return 1.0
    return valid_count / total_count


def exceeds_threshold(
    error_count: int,
    total_count: int,
    soft_threshold: float = 0.05,
    hard_threshold: float = 0.20,
) -> tuple[bool, bool]:
    """Check if error rate exceeds thresholds."""
    if total_count == 0:
        return False, False
    error_rate = error_count / total_count
    return error_rate > soft_threshold, error_rate > hard_threshold


def detect_hash_collision(
    _: ContentHash,
    source_record_id: str,
    existing_source_id: str | None,
) -> bool:
    """Detect content hash collision."""
    return existing_source_id is not None and source_record_id != existing_source_id


def safe_float(value: Any, default: float | None = None) -> float | None:
    """Safely convert value to float.

    Args:
        value: Input value to convert
        default: Default value if conversion fails (default: None)

    Returns:
        Converted float or default value
    """
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int | None = None) -> int | None:
    """Safely convert value to int.

    Args:
        value: Input value to convert
        default: Default value if conversion fails (default: None)

    Returns:
        Converted int or default value
    """
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
