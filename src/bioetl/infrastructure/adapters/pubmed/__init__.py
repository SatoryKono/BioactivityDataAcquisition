"""PubMed adapter components.

This package provides the adapter for interacting with the PubMed API.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.pubmed.models import (
    PUBMED_RECORD_MODELS,
    PubMedArticleRecord,
    PubMedExtendedRecord,
    PubMedSearchResponse,
)
from bioetl.infrastructure.adapters.pubmed.pubmed_client import PubMedAdapter

__all__ = [
    # Model Mappings
    "PUBMED_RECORD_MODELS",
    # Adapter
    "PubMedAdapter",
    # Record Models
    "PubMedArticleRecord",
    "PubMedExtendedRecord",
    # Response Models
    "PubMedSearchResponse",
]
