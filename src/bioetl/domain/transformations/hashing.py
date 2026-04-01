"""Content hash generation transformations (no I/O, deterministic, side-effect free).

Implements RULES.md §2.8 — Entity ID Generation and Content Hashing.
REQ-ID-001..008.

Hashing contract:
- Exclude ``META_FIELDS`` and any underscore-prefixed technical fields.
- Normalize values recursively before hashing.
- Serialize only through canonical JSON.
- The same ``provider + normalized payload`` MUST always produce the same hash.
"""

from __future__ import annotations

import hashlib
import math
from datetime import date, datetime
from functools import singledispatch
from typing import Any  # Any: required for singledispatch base case signature

from bioetl.domain.types import JsonDict

from ..constants import META_FIELDS
from ..serialization import serialize_to_canonical_json
from ..types import ContentHash, EntityID

# =============================================================================
# Singledispatch normalization helpers
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


# =============================================================================
# Field inclusion helpers
# =============================================================================


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


# =============================================================================
# Public API
# =============================================================================


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

    Delegates to ``domain.serialization.serialize_to_canonical_json()``
    for consistent JSON serialization across the codebase.

    Args:
        obj: Dictionary to serialize as canonical JSON.

    Returns:
        Canonical JSON string with sorted keys and no extra whitespace.
    """
    return serialize_to_canonical_json(obj)


def generate_content_hash(
    record: JsonDict,
    provider: str,
    exclude_none: bool = False,
    include_fields: set[str] | None = None,
    exclude_fields: set[str] | None = None,
) -> ContentHash:
    """Generate SHA256 content hash for record versioning.

    The hash material is built from ``provider + canonical_json(normalized_record)``.
    Normalization excludes technical metadata, strips strings, canonicalizes nested
    dictionaries via sorted-key JSON, and preserves list order.

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
