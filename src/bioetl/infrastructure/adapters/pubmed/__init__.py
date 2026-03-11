"""PubMed adapter components.

This package provides the adapter for interacting with the PubMed API.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.pubmed.client import PubMedAdapter
from bioetl.infrastructure.adapters.pubmed.fallback import TitleFallbackHandler
from bioetl.infrastructure.adapters.pubmed.models import (
    PUBMED_RECORD_MODELS,
    PubMedArticleRecord,
    PubMedExtendedRecord,
    PubMedSearchResponse,
)

__all__ = [
    "PUBMED_RECORD_MODELS",
    "PubMedAdapter",
    "PubMedArticleRecord",
    "PubMedExtendedRecord",
    "PubMedSearchResponse",
    "TitleFallbackHandler",
]
