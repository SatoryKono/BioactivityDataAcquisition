"""Entity ID computation utilities.

Pure functions for computing deterministic entity IDs from composite keys.
Used by both transformers and data source wrappers to ensure consistent
entity identification across different pipeline paths.
"""

from __future__ import annotations

import hashlib


def compute_publication_term_entity_id(
    document_chembl_id: str,
    term_type: str,
    term: str,
) -> str:
    """Compute entity ID for a publication term based on composite key.

    Entity ID is SHA256 hash of: document_chembl_id:term_type:normalized_term

    Args:
        document_chembl_id: Document ChEMBL ID.
        term_type: Term type classification.
        term: Term text (will be normalized).

    Returns:
        Entity ID string (first 16 chars of SHA256 hex digest).

    """
    normalized_term = term.lower().strip() if term else ""
    composite = f"{document_chembl_id}:{term_type}:{normalized_term}"
    return hashlib.sha256(composite.encode()).hexdigest()[:16]


def compute_subcellular_fraction_entity_id(
    subcellular_fraction: str,
) -> str:
    """Compute entity ID for a subcellular fraction based on its name.

    Entity ID is SHA256 hash of: normalized_fraction_name

    Args:
        subcellular_fraction: Name of the subcellular fraction.

    Returns:
        Entity ID string (first 16 chars of SHA256 hex digest).

    """
    normalized = subcellular_fraction.lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]
