"""Entity ID computation utilities.

Identity scheme
---------------
``ENTITY_ID_SCHEME_VERSION`` documents the hashing contract for publication-term
and subcellular-fraction entity IDs. Digests are the first 16 hex characters of
SHA-256 over a canonical composite string.

**v2 (current)** — publication term:

- ``publication_id``: CHEMBL id via ``normalize_profile_chembl_id``
- ``term_type``: always ``strip().upper()`` (known and unknown types)
- ``term``: ``normalize_profile_title``
- composite: ``{publication_id}:{term_type}:{term}``

**v2 (current)** — subcellular fraction:

- fraction: governed vocabulary with ``preserve_unknown=True``
- composite: ``subcellular_fraction:{fraction}``

Callers that persist entity IDs must treat scheme version changes as migrations
(see CHANGELOG), not as silent rehashing of historical rows.
"""

from __future__ import annotations

__all__ = [
    "ENTITY_ID_SCHEME_VERSION",
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
    SUBCELLULAR_FRACTIONS,
)

# Explicit scheme marker so identity changes are versioned, not silent (#7777).
ENTITY_ID_SCHEME_VERSION: str = "v2"


def _normalize_publication_term_identity_component(value: str) -> str:
    """Canonicalize publication-term identity components before hashing.

    Always return the trimmed uppercased value so identity hashing is case-stable
    for known and unknown term types alike. Vocabulary membership remains a
    validation concern outside entity-id construction.
    """
    return value.strip().upper()


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
    if not normalized_publication_id or not normalized_term_type or not normalized_term:
        raise ValueError(
            "publication-term identity requires non-empty publication_id, "
            "term_type, and term after normalization"
        )
    composite = f"{normalized_publication_id}:{normalized_term_type}:{normalized_term}"
    return hashlib.sha256(composite.encode()).hexdigest()[:16]


def compute_subcellular_fraction_entity_id(subcellular_fraction: str) -> str:
    """Compute entity ID from the canonical subcellular-fraction value."""
    normalized_fraction = _normalize_subcellular_fraction_value(subcellular_fraction)
    composite = f"subcellular_fraction:{normalized_fraction}"
    return hashlib.sha256(composite.encode()).hexdigest()[:16]
