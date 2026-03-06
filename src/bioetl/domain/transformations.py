"""Pure domain transformations (no I/O, deterministic, side-effect free).

Implements RULES.md §2.8 — Entity ID Generation and Content Hashing.
REQ-ARCH-003, REQ-ID-001..008, REQ-SCHEMA-001..004.
"""

from __future__ import annotations

import hashlib
import math
from datetime import date, datetime
from functools import singledispatch
from typing import Any  # Any: required for singledispatch base case signature

from bioetl.domain.types import JsonDict

from .constants import META_FIELDS
from .serialization import serialize_to_json_canonical
from .types import ContentHash, DriftLevel, EntityID

__all__ = [
    "calculate_dq_score",
    "canonical_json_dumps",
    "detect_hash_collision",
    "detect_schema_drift",
    "exceeds_threshold",
    "generate_content_hash",
    "generate_entity_id",
    "normalize_for_hash",
    "safe_float",
    "safe_int",
    "safe_str",
]


# =============================================================================
# Content Hash Generation (RULES.md §2.8)
# =============================================================================


@singledispatch
def _normalize_value(
    value: Any,  # Any: singledispatch requires Any for dispatch
) -> Any:  # Any: singledispatch requires Any for dispatch
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
def _normalize_dict(value: JsonDict) -> JsonDict:
    """Normalize dict by recursively normalizing values."""
    return {k: _normalize_value(v) for k, v in value.items()}


@_normalize_value.register(list)
def _normalize_list(value: list[object]) -> list[object]:
    """Normalize list by recursively normalizing elements."""
    return [_normalize_value(v) for v in value]


# Keep registry visible for tooling to avoid false dead-code positives.
_NORMALIZE_DISPATCH = (
    _normalize_float,
    _normalize_datetime,
    _normalize_date,
    _normalize_str,
    _normalize_dict,
    _normalize_list,
)


def _is_excluded_key(
    key: str,
    exclude_fields: set[str] | None,
) -> bool:
    """Check if key is excluded by explicit set, prefix, or META_FIELDS."""
    if exclude_fields and key in exclude_fields:
        return True
    return key.startswith("_") or key in META_FIELDS


def _should_include_field(
    key: str,
    value: object,
    exclude_none: bool,
    include_fields: set[str] | None = None,
    exclude_fields: set[str] | None = None,
) -> bool:
    """Check if field should be included in hash calculation."""
    if exclude_none and value is None:
        return False
    if _is_excluded_key(key, exclude_fields):
        return False
    if include_fields is not None:
        return key in include_fields
    return True


def normalize_for_hash(
    record: JsonDict,
    exclude_none: bool = False,
    include_fields: set[str] | None = None,
    exclude_fields: set[str] | None = None,
) -> JsonDict:
    """Normalize record before hashing to ensure consistency.

    Args:
        record: Single data record.
        exclude_none: Whether to exclude None values from the normalized result.
        include_fields: Set of field names to include (if specified, only these fields are kept).
        exclude_fields: Set of field names to exclude from normalization.

    Returns:
        Normalized dictionary with consistent value representations.
    """
    return {
        key: _normalize_value(value)
        for key, value in record.items()
        if _should_include_field(
            key, value, exclude_none, include_fields, exclude_fields
        )
    }


def canonical_json_dumps(obj: JsonDict) -> str:
    """Convert object to canonical JSON representation.

    Delegates to domain.serialization.serialize_to_json_canonical()
    for consistent JSON serialization across the codebase.

    Args:
        obj: Dictionary to serialize as canonical JSON.

    Returns:
        Canonical JSON string with sorted keys and no extra whitespace.
    """
    return serialize_to_json_canonical(obj)


def generate_content_hash(
    record: JsonDict,
    provider: str,
    exclude_none: bool = False,
    include_fields: set[str] | None = None,
    exclude_fields: set[str] | None = None,
) -> ContentHash:
    """Generate SHA256 content hash for record versioning.

    Args:
        record: Single data record.
        provider: Data provider name.
        exclude_none: Whether to exclude None values from hash computation.
        include_fields: Set of field names to include (if specified, only these fields are hashed).
        exclude_fields: Set of field names to exclude from hash computation.

    Returns:
        SHA256 content hash of the normalized record.
    """
    normalized = normalize_for_hash(
        record,
        exclude_none=exclude_none,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
    )
    canonical = canonical_json_dumps(normalized)
    data = f"{provider}{canonical}"
    hash_digest = hashlib.sha256(data.encode("utf-8")).hexdigest()
    return ContentHash(hash_digest)


def generate_entity_id(
    record: JsonDict,
    provider: str,
    id_field: str | None = None,
) -> EntityID:
    """Generate stable entity ID (business key).

    Args:
        record: Single data record.
        provider: Data provider name.
        id_field: Name of the field containing the business key (if None, uses content hash).

    Returns:
        Stable entity identifier in format 'provider:key'.
    """
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
) -> tuple[DriftLevel, JsonDict]:
    """Detect schema drift between two schemas.

    Args:
        old_schema: Set of field names in the previous schema version.
        new_schema: Set of field names in the current schema version.
        required_fields: Set of fields that must not be removed (triggers CRITICAL drift).

    Returns:
        Tuple of (drift_level, details_dict) with added/removed fields info.
    """
    added = sorted(new_schema - old_schema)
    removed = sorted(old_schema - new_schema)
    missing_required = sorted((required_fields or set()) & set(removed))

    level = DriftLevel.INFO
    if missing_required:
        level = DriftLevel.CRITICAL

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
    """Calculate data quality score (0.0 to 1.0).

    Args:
        valid_count: Number of records that passed validation.
        total_count: Total number of records processed.

    Returns:
        Quality score ratio between 0.0 and 1.0 (1.0 if total is zero).
    """
    if total_count == 0:
        return 1.0
    return valid_count / total_count


def exceeds_threshold(
    error_count: int,
    total_count: int,
    soft_threshold: float = 0.05,
    hard_threshold: float = 0.20,
) -> tuple[bool, bool]:
    """Check if error rate exceeds thresholds.

    Args:
        error_count: Number of records with errors.
        total_count: Total number of records processed.
        soft_threshold: Warning threshold ratio (default 5%).
        hard_threshold: Failure threshold ratio (default 20%).

    Returns:
        Tuple of (exceeds_soft, exceeds_hard) booleans.
    """
    if total_count == 0:
        return False, False
    error_rate = error_count / total_count
    return error_rate > soft_threshold, error_rate > hard_threshold


def detect_hash_collision(
    _: ContentHash,
    source_record_id: str,
    existing_source_id: str | None,
) -> bool:
    """Detect content hash collision.

    Args:
        _: Content hash (unused, kept for API compatibility).
        source_record_id: ID of the incoming record.
        existing_source_id: ID of the record already stored with the same hash.

    Returns:
        True if a collision is detected (same hash, different source IDs).
    """
    return existing_source_id is not None and source_record_id != existing_source_id


_SAFE_CONVERT_SKIP: tuple[type, ...] = (type(None), bool)


def _coerce_to_float(value: object) -> float:
    """Coerce non-None/non-bool value to float; raises on failure."""
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).strip())


def _coerce_to_int(value: object) -> int | None:
    """Coerce non-None/non-bool value to int; returns None for non-finite floats."""
    if isinstance(value, float):
        return int(value) if math.isfinite(value) else None
    if isinstance(value, int):
        return value
    return int(str(value).strip())


def safe_float(
    value: object,
    default: float | None = None,
) -> float | None:
    """Safely convert *value* to float, returning *default* on failure.

    Returns:
        Converted float value, or default if conversion fails or value is non-finite.
    """
    if isinstance(value, _SAFE_CONVERT_SKIP):
        return default
    try:
        converted = _coerce_to_float(value)
        return converted if math.isfinite(converted) else default
    except (ValueError, TypeError):
        return default


def safe_int(
    value: object,
    default: int | None = None,
) -> int | None:
    """Safely convert *value* to int, returning *default* on failure.

    Returns:
        Converted integer value, or default if conversion fails or value is non-finite.
    """
    if isinstance(value, _SAFE_CONVERT_SKIP):
        return default
    try:
        result = _coerce_to_int(value)
        return result if result is not None else default
    except (ValueError, TypeError):
        return default


def safe_str(
    value: object,
    default: str | None = None,
) -> str | None:
    """Safely convert value to string.

    Useful for fields that may come as int/float from API but need to be
    stored as strings in the schema.

    Args:
        value: Input value to convert
        default: Default value if conversion fails (default: None)

    Returns:
        Converted string or default value
    """
    if value is None:
        return default
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    try:
        return str(value)
    except (ValueError, TypeError):
        return default
