"""Utilities for publication term entity identifiers."""

from __future__ import annotations

import hashlib


def compute_publication_term_entity_id(
    document_chembl_id: str,
    term_type: str,
    term: str,
) -> str:
    """Compute stable publication term entity ID from composite key."""
    normalized_term = term.lower().strip() if term else ""
    composite = f"{document_chembl_id}:{term_type}:{normalized_term}"
    return hashlib.sha256(composite.encode()).hexdigest()[:16]
