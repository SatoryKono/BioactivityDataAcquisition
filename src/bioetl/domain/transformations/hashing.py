"""Content hash generation transformations (no I/O, deterministic, side-effect free).

Implements RULES.md §2.8 — Entity ID Generation and Content Hashing.
REQ-ID-001..008.

Hashing contract:
- Exclude ``META_FIELDS`` and any underscore-prefixed technical fields.
- Normalize values recursively through the canonical hash-identity contract.
- Serialize only through canonical hash-identity JSON.
- The same ``provider + normalized payload`` MUST always produce the same hash.
"""

from __future__ import annotations

import hashlib

from bioetl.domain.normalization.hash_identity import (
    HashDatetimePolicy,
    normalize_hash_identity_record,
    serialize_hash_identity_canonical_json,
)
from bioetl.domain.types import JsonDict

from ..constants import META_FIELDS
from ..types import ContentHash, EntityID

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
    set_like_fields: set[str] | None = None,
    datetime_policy: HashDatetimePolicy = "v1_date",
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
    filtered = {
        key: value
        for key, value in record.items()
        if _should_include_field(
            key, value, exclude_none, include_fields, exclude_fields
        )
    }
    return normalize_hash_identity_record(
        filtered,
        exclude_none=exclude_none,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
        sort_nested_sequence_fields=set_like_fields,
        datetime_policy=datetime_policy,
    )


def canonical_json_dumps(obj: JsonDict) -> str:
    """Convert object to canonical JSON representation.

    Delegates to ``domain.serialization.serialize_to_canonical_json()``
    for consistent JSON serialization across the codebase.

    Args:
        obj: Dictionary to serialize as canonical JSON.

    Returns:
        Canonical JSON string with sorted keys and no extra whitespace.
    """
    return serialize_hash_identity_canonical_json(obj)


def generate_content_hash(
    record: JsonDict,
    provider: str,
    exclude_none: bool = False,
    include_fields: set[str] | None = None,
    exclude_fields: set[str] | None = None,
    set_like_fields: set[str] | None = None,
    datetime_policy: HashDatetimePolicy = "v1_date",
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
        set_like_fields=set_like_fields,
        datetime_policy=datetime_policy,
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
