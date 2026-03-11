"""Canonical PubMed adapter entrypoint.

Keeps backward compatibility while steering new imports away from
``pubmed_client``.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.pubmed.pubmed_client import (
    ENTREZ_API_BASE,
    PubMedAdapter,
    _create_pubmed_adapter,
)

__all__ = ["ENTREZ_API_BASE", "PubMedAdapter", "_create_pubmed_adapter"]
