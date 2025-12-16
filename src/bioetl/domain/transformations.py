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
from collections.abc import Mapping, Sequence
from datetime import date, datetime
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


def normalize_for_hash(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize record before hashing to ensure consistency.

    Requirements:
    - REQ-ID-004: NaN/Inf → null
    - REQ-ID-003: Floats → round(10)
    - REQ-ID-005: Dates → ISO format (YYYY-MM-DD)
    - REQ-ID-006: Strings → strip()
    - REQ-ID-007: Exclude meta-fields

    Args:
        record: Raw record dictionary

    Returns:
        Normalized record ready for canonical JSON

    Example:
        >>> normalize_for_hash({
        ...     "value": 3.141592653589793,
        ...     "date": datetime(2025, 12, 15),
        ...     "name": "  aspirin  ",
        ...     "_run_id": "uuid-123"
        ... })
        {'value': 3.1415926536, 'date': '2025-12-15', 'name': 'aspirin'}
    """
    normalized = {}

    for key, value in record.items():
        # Skip meta-fields (REQ-ID-007)
        if key in META_FIELDS:
            continue

        # Normalize value
        normalized[key] = _normalize_value(value)

    return normalized


def _normalize_float(value: float) -> float | None:
    """Normalize a float value, handling NaN/Inf."""
    # NaN/Inf → null (REQ-ID-004)
    if math.isnan(value) or math.isinf(value):
        return None
    # Round to 10 decimals (REQ-ID-003)
    return round(value, 10)


def _normalize_date(value: date) -> str:
    """Normalize a date value to ISO format."""
    return value.isoformat()


def _normalize_datetime(value: datetime) -> str:
    """Normalize a datetime value to ISO date format."""
    return value.date().isoformat()


def _normalize_mapping(value: Mapping) -> dict:
    """Recursively normalize a mapping."""
    return {k: _normalize_value(v) for k, v in value.items()}


def _normalize_sequence(value: Sequence) -> list:
    """Recursively normalize a sequence."""
    return [_normalize_value(v) for v in value]


# Type dispatch table for normalization (reduces cyclomatic complexity)
_NORMALIZERS: dict[type, Any] = {
    float: _normalize_float,
    datetime: _normalize_datetime,
    date: _normalize_date,
}


def _normalize_value(value: Any) -> Any:
    """Normalize a single value using type dispatch."""
    # Check exact type match first
    normalizer = _NORMALIZERS.get(type(value))
    if normalizer is not None:
        return normalizer(value)

    # Handle strings (strip whitespace)
    if isinstance(value, str):
        return value.strip()

    # Handle nested structures
    if isinstance(value, Mapping):
        return _normalize_mapping(value)
    if isinstance(value, Sequence):
        return _normalize_sequence(value)

    return value


def canonical_json_dumps(obj: dict[str, Any]) -> str:
    """Convert object to canonical JSON representation.

    Requirements:
    - REQ-ID-002: sort_keys=True, separators=(',', ':'), ensure_ascii=True

    Args:
        obj: Normalized dictionary

    Returns:
        Canonical JSON string

    Example:
        >>> canonical_json_dumps({"b": 2, "a": 1})
        '{"a":1,"b":2}'
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def generate_content_hash(record: dict[str, Any], provider: str) -> ContentHash:
    """Generate SHA256 content hash for record versioning.

    Requirements:
    - REQ-ID-001: sha256(provider + canonical_json(record))

    Args:
        record: Raw record dictionary
        provider: Provider name (e.g., 'chembl', 'pubchem')

    Returns:
        SHA256 hex digest as ContentHash

    Example:
        >>> record = {"id": "CHEMBL123", "value": 5.5}
        >>> hash_val = generate_content_hash(record, "chembl")
        >>> len(hash_val)  # SHA256 hex = 64 chars
        64
    """
    # Normalize record
    normalized = normalize_for_hash(record)

    # Canonical JSON
    canonical = canonical_json_dumps(normalized)

    # Hash: sha256(provider + canonical_json)
    data = f"{provider}{canonical}"
    hash_digest = hashlib.sha256(data.encode("utf-8")).hexdigest()

    return ContentHash(hash_digest)


def generate_entity_id(
    record: dict[str, Any],
    provider: str,
    id_field: str | None = None,
) -> EntityID:
    """Generate stable entity ID (business key).

    Strategy (RULES.md §2.8):
    - If source provides stable ID: use as-is (e.g., chembl_id, pubchem_cid)
    - Otherwise: use content hash

    Args:
        record: Raw record
        provider: Provider name
        id_field: Field containing stable ID (None = use content hash)

    Returns:
        Entity ID

    Example:
        >>> # With stable ID
        >>> generate_entity_id({"chembl_id": "CHEMBL123"}, "chembl", "chembl_id")
        EntityID('chembl:CHEMBL123')

        >>> # Without stable ID (fallback to hash)
        >>> generate_entity_id({"name": "aspirin"}, "custom", None)
        EntityID('custom:a3f2...')  # Content hash
    """
    if id_field and id_field in record:
        # Use stable ID from source
        stable_id = str(record[id_field])
        return EntityID(f"{provider}:{stable_id}")

    # Fallback: content hash
    content_hash = generate_content_hash(record, provider)
    return EntityID(f"{provider}:{content_hash[:16]}")  # First 16 chars


# =============================================================================
# Schema Drift Detection (RULES.md §2.2)
# =============================================================================


def _build_drift_details(
    added: list[str],
    removed: list[str],
    missing_required: list[str] | None = None,
) -> dict[str, Any]:
    """Build drift details dictionary."""
    details: dict[str, Any] = {
        "added_fields": added,
        "removed_fields": removed,
        "field_count_delta": len(added) - len(removed),
    }
    if missing_required:
        details["missing_required"] = missing_required
    return details


def _determine_drift_level(
    added_count: int,
    has_changes: bool,
    missing_required: set[str],
) -> DriftLevel:
    """Determine drift level based on changes."""
    if missing_required:
        return DriftLevel.CRITICAL
    if added_count > 3:
        return DriftLevel.WARN
    return DriftLevel.INFO


def detect_schema_drift(
    old_schema: set[str],
    new_schema: set[str],
    required_fields: set[str] | None = None,
) -> tuple[DriftLevel, dict[str, Any]]:
    """Detect schema drift between two schemas.

    Drift Levels (RULES.md §2.2):
    - INFO: New optional fields appear
    - WARN: >3 new fields appear (requires review within 48h)
    - CRITICAL: Required fields (ID) disappear (blocks pipeline)

    Args:
        old_schema: Set of field names from previous schema
        new_schema: Set of field names from current schema
        required_fields: Set of required field names (e.g., {'id', 'entity_id'})

    Returns:
        (drift_level, drift_details) where drift_details contains:
        - added_fields: List of newly added fields
        - removed_fields: List of removed fields
        - field_count_delta: Change in field count
    """
    required_fields = required_fields or set()

    added = sorted(new_schema - old_schema)
    removed = sorted(old_schema - new_schema)
    missing_required = required_fields & set(removed)

    level = _determine_drift_level(len(added), bool(added or removed), missing_required)
    details = _build_drift_details(added, removed, sorted(missing_required) or None)

    return level, details


# =============================================================================
# Data Quality Helpers
# =============================================================================


def calculate_dq_score(valid_count: int, total_count: int) -> float:
    """Calculate data quality score (0.0 to 1.0).

    Args:
        valid_count: Number of valid records
        total_count: Total number of records

    Returns:
        Quality score (1.0 = perfect, 0.0 = all invalid)

    Example:
        >>> calculate_dq_score(95, 100)
        0.95
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

    Requirements:
    - REQ-THRESHOLD-001: >5% → Warning (soft)
    - REQ-THRESHOLD-002: >20% → Fail (hard)

    Args:
        error_count: Number of errors
        total_count: Total records
        soft_threshold: Warning threshold (default 5%)
        hard_threshold: Critical threshold (default 20%)

    Returns:
        (soft_exceeded, hard_exceeded)

    Example:
        >>> exceeds_threshold(6, 100)  # 6% error rate
        (True, False)  # Soft threshold exceeded

        >>> exceeds_threshold(25, 100)  # 25% error rate
        (True, True)  # Both thresholds exceeded
    """
    if total_count == 0:
        return (False, False)

    error_rate = error_count / total_count
    soft_exceeded = error_rate > soft_threshold
    hard_exceeded = error_rate > hard_threshold

    return (soft_exceeded, hard_exceeded)


def detect_hash_collision(
    _: ContentHash,
    source_record_id: str,
    existing_source_id: str | None,
) -> bool:
    """Detect content hash collision.

    Requirements:
    - REQ-ID-008: Log both records if collision detected

    Args:
        content_hash: Generated content hash
        source_record_id: ID from source record
        existing_source_id: ID from existing record with same hash

    Returns:
        True if collision detected (different source IDs, same hash)

    Example:
        >>> detect_hash_collision("abc123", "id_1", "id_2")
        True  # Collision: same hash, different IDs

        >>> detect_hash_collision("abc123", "id_1", "id_1")
        False  # No collision: same record
    """
    if existing_source_id is None:
        return False

    return source_record_id != existing_source_id
