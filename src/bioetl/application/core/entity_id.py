"""Entity ID computation utilities."""

from __future__ import annotations

__all__ = [
    "compute_publication_term_entity_id",
    "compute_subcellular_fraction_entity_id",
]

import hashlib

from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_chembl_id,
    normalize_profile_governed_vocabulary,
    normalize_profile_title,
)
from bioetl.domain.schemas.constants import (
    PUBLICATION_TERM_TYPES,
    SUBCELLULAR_FRACTIONS,
)


def _normalize_publication_term_identity_component(value: str) -> str:
    """Canonicalize publication-term identity components before hashing."""
    normalized = value.strip()
    upper_value = normalized.upper()
    if upper_value in PUBLICATION_TERM_TYPES:
        return upper_value
    return normalized


def _normalize_publication_id(value: str) -> str:
    """Canonicalize publication identity to the shared CHEMBL identifier form."""
    normalized = normalize_profile_chembl_id(value)
    return normalized if isinstance(normalized, str) else ""


def _normalize_publication_term_value(value: str) -> str:
    """Canonicalize publication-term text before computing the digest."""
    normalized = normalize_profile_title(value)
    return normalized if isinstance(normalized, str) else ""


def _normalize_subcellular_fraction_value(value: str) -> str:
    """Canonicalize subcellular fractions with the shared governed vocabulary."""
    normalized = normalize_profile_governed_vocabulary(
        normalize_profile_title(value),
        allowed_values=SUBCELLULAR_FRACTIONS,
        preserve_unknown=True,
    )
    return normalized if isinstance(normalized, str) else ""


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
    normalized_publication_id = _normalize_publication_id(publication_id)
    normalized_term_type = _normalize_publication_term_identity_component(term_type)
    normalized_term = _normalize_publication_term_value(term)
    composite = f"{normalized_publication_id}:{normalized_term_type}:{normalized_term}"
    return hashlib.sha256(composite.encode()).hexdigest()[:16]


def compute_subcellular_fraction_entity_id(subcellular_fraction: str) -> str:
    """Compute entity ID from the canonical subcellular-fraction value."""
    normalized_fraction = _normalize_subcellular_fraction_value(subcellular_fraction)
    composite = f"subcellular_fraction:{normalized_fraction}"
    return hashlib.sha256(composite.encode()).hexdigest()[:16]
