"""Entity identity generator for deterministic IDs and content hashes.

Provides centralized logic for computing entity identifiers and content hashes
according to RULES.md §2.8.

Delegates normalization and hashing to the canonical implementations in
``bioetl.domain.transformations`` to avoid algorithm duplication (DRY).

This is a pure domain service with no external dependencies (only stdlib).
All methods are deterministic and side-effect free.

Requirements:
- REQ-ID-001 to REQ-ID-008: Content hash algorithm
- REQ-ARCH-003: No I/O in domain layer
"""

from __future__ import annotations

from bioetl.domain.constants import META_FIELDS
from bioetl.domain.transformations import (
    generate_content_hash,
    normalize_for_hash,
)
from bioetl.domain.types import ContentHash, EntityID, JsonDict

__all__ = [
    "META_FIELDS",
    "EntityIdentityGenerator",
]


class EntityIdentityGenerator:
    """Generator for entity identifiers and content hashes.

    This is the canonical domain facade for content hashing. It delegates to the
    single hashing implementation in ``bioetl.domain.transformations`` so callers
    cannot accidentally diverge on metadata exclusion or canonical JSON behavior.

    Implements RULES.md §2.8 entity identification:
    - Stable entity_id from business keys or content hash
    - SHA256 content hash with canonical JSON normalization
    - Meta-field exclusion for deterministic hashing

    All normalization and hashing logic is delegated to the canonical
    free functions in ``bioetl.domain.transformations`` to maintain a
    single source of truth for the hash algorithm (DRY principle).

    This service is stateless and can be safely shared across transformers.
    All methods are pure (deterministic, side-effect free).

    Example:
        >>> identity = EntityIdentityGenerator()
        >>> entity_id = identity.compute_entity_id(
        ...     provider="chembl",
        ...     entity_type="activity",
        ...     source_id="12345",
        ...     record={"activity_id": "12345", "value": 100.0},
        ... )
        >>> content_hash = identity.compute_content_hash(
        ...     provider="chembl",
        ...     record={"activity_id": "12345", "value": 100.0},
        ... )

    """

    def __init__(
        self,
        *,
        content_hash_include_fields: set[str] | None = None,
        content_hash_exclude_fields: set[str] | None = None,
    ) -> None:
        """Initialize service with optional default content-hash field policy."""
        self._content_hash_include_fields = content_hash_include_fields
        self._content_hash_exclude_fields = content_hash_exclude_fields or set()

    def compute_entity_id(
        self,
        provider: str,
        entity_type: str,
        source_id: str | None,
        record: JsonDict,  # Any: record values are heterogeneous
    ) -> EntityID:
        """Compute stable entity identifier.

        If source_id is provided, uses it directly for stable identification.
        Otherwise, generates identifier from content hash prefix.

        Delegates to ``bioetl.domain.transformations.generate_entity_id``.

        Args:
            provider: Data provider identifier (e.g., 'chembl', 'pubchem').
            entity_type: Entity type (e.g., 'activity', 'compound'). Reserved for future.
            source_id: Source system identifier (e.g., activity_id from API).
            record: Full record for fallback hash-based identification.

        Returns:
            EntityID in format "{provider}:{id}" or "{provider}:{hash_prefix}".

        Example:
            >>> identity.compute_entity_id("chembl", "activity", "12345", {})
            EntityID("chembl:12345")
            >>> identity.compute_entity_id("chembl", "activity", None, {"val": 1})
            EntityID("chembl:a1b2c3d4e5f6...")  # hash-based

        """
        del entity_type
        if source_id:
            return EntityID(f"{provider}:{source_id}")

        # Fallback: generate from content hash prefix
        content_hash = self.compute_content_hash(provider, record)
        return EntityID(f"{provider}:{content_hash[:16]}")

    def compute_content_hash(
        self,
        provider: str,
        record: JsonDict,  # Any: record values are heterogeneous
        *,
        exclude_none: bool = False,
        include_fields: set[str] | None = None,
        exclude_fields: set[str] | None = None,
    ) -> ContentHash:
        """Compute SHA256 content hash for record versioning.

        Delegates to ``bioetl.domain.transformations.generate_content_hash``.

        Implements RULES.md §2.8.1:
        - sha256(provider + canonical_json(record))
        - Excludes ``META_FIELDS`` and underscore-prefixed technical fields
        - Normalizes values before hashing for consistency

        Args:
            provider: Data provider identifier (e.g., 'chembl', 'pubchem').
            record: Business data dictionary (meta fields auto-excluded).
            exclude_none: Whether to exclude None values from hash.
            include_fields: Optional explicit set of fields to include in the
                hash, overriding the instance-level default include policy.
            exclude_fields: Optional additional set of fields to exclude from
                the hash, merged with the instance-level exclude policy.

        Returns:
            ContentHash (SHA256 hex digest, 64 characters).

        Example:
            >>> identity.compute_content_hash("chembl", {"id": "123", "val": 1.0})
            ContentHash("abc123...")

        """
        resolved_include_fields = (
            include_fields
            if include_fields is not None
            else self._content_hash_include_fields
        )
        resolved_exclude_fields = self._content_hash_exclude_fields | (
            exclude_fields or set()
        )
        return generate_content_hash(
            record,
            provider,
            exclude_none=exclude_none,
            include_fields=resolved_include_fields,
            exclude_fields=resolved_exclude_fields,
        )

    def _normalize_for_hash(
        self,
        record: JsonDict,  # Any: record values are heterogeneous
        *,
        exclude_none: bool = False,
        include_fields: set[str] | None = None,
        exclude_fields: set[str] | None = None,
    ) -> JsonDict:  # Any: record values are heterogeneous
        """Normalize record before hashing for consistency.

        Delegates to ``bioetl.domain.transformations.normalize_for_hash``.

        Applies normalization rules from RULES.md §2.8.1:
        - NaN/Inf floats -> null
        - Floats -> round(val, 10)
        - Dates -> ISO YYYY-MM-DD
        - Strings -> strip()
        - Meta-fields (_ingestion_ts, _run_id, etc.) -> excluded

        Args:
            record: Input record dictionary.
            exclude_none: Whether to exclude None values.

        Returns:
            Normalized dictionary suitable for hashing.

        """
        resolved_include_fields = (
            include_fields
            if include_fields is not None
            else self._content_hash_include_fields
        )
        resolved_exclude_fields = self._content_hash_exclude_fields | (
            exclude_fields or set()
        )
        return normalize_for_hash(
            record,
            exclude_none=exclude_none,
            include_fields=resolved_include_fields,
            exclude_fields=resolved_exclude_fields,
        )
