"""PubMed adapter components.

This package provides the adapter for interacting with the PubMed API.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.pubmed._adapter_support import (
    _create_pubmed_adapter as create_pubmed_adapter,
)
from bioetl.infrastructure.adapters.pubmed.adapter import (
    ENTREZ_API_BASE,
    PubMedAdapter,
)
from bioetl.infrastructure.adapters.pubmed.fallback import PubMedTitleFallbackHandler
from bioetl.infrastructure.adapters.pubmed.models import (
    PUBMED_RECORD_MODELS,
    PubMedArticleRecord,
    PubMedExtendedRecord,
    PubMedSearchResponse,
)

__all__ = [
    "ENTREZ_API_BASE",
    "PUBMED_RECORD_MODELS",
    "PubMedAdapter",
    "PubMedArticleRecord",
    "PubMedExtendedRecord",
    "PubMedSearchResponse",
    "PubMedTitleFallbackHandler",
    "create_pubmed_adapter",
]
