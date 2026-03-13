"""PubMed adapter entrypoint.

Stable canonical import path — use this module (or the package
``bioetl.infrastructure.adapters.pubmed``) for all imports.
Implementation lives in ``pubmed_client``.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.pubmed.pubmed_client import (
    ENTREZ_API_BASE,
    PubMedAdapter,
    _create_pubmed_adapter,
)

__all__ = ["ENTREZ_API_BASE", "PubMedAdapter", "_create_pubmed_adapter"]
