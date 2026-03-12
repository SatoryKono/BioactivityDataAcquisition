"""Retained PubMed adapter entrypoint.

This module is the stable canonical import path for first-party code. It
remains intentionally retained in the current cycle while the implementation
continues to live in ``pubmed_client``.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.pubmed.pubmed_client import (
    ENTREZ_API_BASE,
    PubMedAdapter,
    _create_pubmed_adapter,
)

__all__ = ["ENTREZ_API_BASE", "PubMedAdapter", "_create_pubmed_adapter"]
