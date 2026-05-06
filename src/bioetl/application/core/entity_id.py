"""Entity ID computation utilities.

Pure functions for computing deterministic entity IDs from composite keys.
Used by both transformers and data source wrappers to ensure consistent
entity identification across different pipeline paths.
"""

from __future__ import annotations

__all__ = ["compute_publication_term_entity_id"]


import hashlib

from bioetl.domain.schemas.constants import PUBLICATION_TERM_TYPES


def _normalize_publication_term_identity_component(value: str) -> str:
    """Canonicalize publication-term identity components before hashing."""
    normalized = value.strip()
    upper_value = normalized.upper()
    if upper_value in PUBLICATION_TERM_TYPES:
        return upper_value
    return normalized


def compute_publication_term_entity_id(
    publication_id: str,
    term_type: str,
    term: str,
) -> str:
    """Compute entity ID for a publication term based on composite key.

    Entity ID is SHA256 hash of: publication_id:term_type:normalized_term

    Args:
        publication_id: Document ChEMBL ID.
        term_type: Term type classification.
        term: Term text (will be normalized).

    Returns:
        Entity ID string (first 16 chars of SHA256 hex digest).

    """
    normalized_publication_id = publication_id.strip() if publication_id else ""
    normalized_term_type = _normalize_publication_term_identity_component(term_type)
    normalized_term = term.lower().strip() if term else ""
    composite = (
        f"{normalized_publication_id}:{normalized_term_type}:{normalized_term}"
    )
    return hashlib.sha256(composite.encode()).hexdigest()[:16]
