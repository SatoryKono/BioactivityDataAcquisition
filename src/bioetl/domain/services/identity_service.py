"""Identity Service for entity identification and content hashing.

Provides centralized logic for computing entity identifiers and content hashes
according to RULES.md §2.8.

This is a pure domain service with no external dependencies (only stdlib).
All methods are deterministic and side-effect free.

Requirements:
- REQ-ID-001 to REQ-ID-008: Content hash algorithm
- REQ-ARCH-003: No I/O in domain layer
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime
from typing import Any

from bioetl.domain.types import ContentHash, EntityID

# Meta-fields to exclude from hash calculation (RULES.md §2.8.1)
META_FIELDS: frozenset[str] = frozenset(
    {
        "_ingestion_ts",
        "_run_id",
        "_run_type",
        "_dq_warn",
        "_dq_error",
        "_source_batch_id",
    }
)


class IdentityService:
    """Service for generating entity identifiers and content hashes.

    Implements RULES.md §2.8 entity identification:
    - Stable entity_id from business keys or content hash
    - SHA256 content hash with canonical JSON normalization
    - Meta-field exclusion for deterministic hashing

    This service is stateless and can be safely shared across transformers.
    All methods are pure (deterministic, side-effect free).

    Example:
        >>> identity = IdentityService()
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

    def compute_entity_id(
        self,
        provider: str,
        entity_type: str,  # noqa: ARG002 - reserved for future use
        source_id: str | None,
        record: dict[str, Any],
    ) -> EntityID:
        """Compute stable entity identifier.

        If source_id is provided, uses it directly for stable identification.
        Otherwise, generates identifier from content hash prefix.

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
        if source_id:
            return EntityID(f"{provider}:{source_id}")

        # Fallback: generate from content hash prefix
        content_hash = self.compute_content_hash(provider, record)
        return EntityID(f"{provider}:{content_hash[:16]}")

    def compute_content_hash(
        self,
        provider: str,
        record: dict[str, Any],
        *,
        exclude_none: bool = False,
    ) -> ContentHash:
        """Compute SHA256 content hash for record versioning.

        Implements RULES.md §2.8.1:
        - sha256(provider + canonical_json(record))
        - Normalizes values before hashing for consistency

        Args:
            provider: Data provider identifier (e.g., 'chembl', 'pubchem').
            record: Business data dictionary (meta fields auto-excluded).
            exclude_none: Whether to exclude None values from hash.

        Returns:
            ContentHash (SHA256 hex digest, 64 characters).

        Example:
            >>> identity.compute_content_hash("chembl", {"id": "123", "val": 1.0})
            ContentHash("abc123...")

        """
        normalized = self._normalize_for_hash(record, exclude_none=exclude_none)
        canonical = self._canonical_json_dumps(normalized)
        data = f"{provider}{canonical}"
        hash_digest = hashlib.sha256(data.encode("utf-8")).hexdigest()
        return ContentHash(hash_digest)

    def _normalize_for_hash(
        self,
        record: dict[str, Any],
        *,
        exclude_none: bool = False,
    ) -> dict[str, Any]:
        """Normalize record before hashing for consistency.

        Applies normalization rules from RULES.md §2.8.1:
        - NaN/Inf floats → null
        - Floats → round(val, 10)
        - Dates → ISO YYYY-MM-DD
        - Strings → strip()
        - Meta-fields (_ingestion_ts, _run_id, etc.) → excluded

        Args:
            record: Input record dictionary.
            exclude_none: Whether to exclude None values.

        Returns:
            Normalized dictionary suitable for hashing.

        """
        result: dict[str, Any] = {}

        for key, value in record.items():
            # Skip meta-fields
            if key in META_FIELDS:
                continue

            # Optionally skip None values
            if exclude_none and value is None:
                continue

            # Normalize and include
            result[key] = self._normalize_value(value)

        return result

    def _normalize_value(self, value: Any) -> Any:
        """Normalize a single value for hashing.

        Args:
            value: Input value of any type.

        Returns:
            Normalized value.

        """
        if value is None:
            return None
        return self._normalize_by_type(value)

    def _normalize_by_type(self, value: Any) -> Any:
        """Dispatch normalization by type."""
        # Handle scalar types first
        scalar_result = self._normalize_scalar(value)
        if scalar_result is not value:  # Was processed
            return scalar_result

        # Handle container types
        return self._normalize_container(value)

    def _normalize_scalar(self, value: Any) -> Any:
        """Normalize scalar types: float, datetime, date, str."""
        if isinstance(value, float):
            return self._normalize_float(value)
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str):
            return value.strip()
        return value  # Return unchanged if not a scalar type we handle

    def _normalize_container(self, value: Any) -> Any:
        """Normalize container types: dict, list."""
        if isinstance(value, dict):
            return {k: self._normalize_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._normalize_value(v) for v in value]
        return value

    def _normalize_float(self, value: float) -> float | None:
        """Normalize float value: NaN/Inf → None, else round to 10 decimals."""
        if math.isnan(value) or math.isinf(value):
            return None
        return round(value, 10)

    @staticmethod
    def _canonical_json_dumps(obj: dict[str, Any]) -> str:
        """Convert object to canonical JSON representation.

        Uses sorted keys and minimal separators for deterministic output.

        Args:
            obj: Dictionary to serialize.

        Returns:
            Canonical JSON string.

        """
        return json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
