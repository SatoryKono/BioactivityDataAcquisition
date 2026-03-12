"""CrossRef adapter for publication metadata enrichment.

Provides DOI resolution and citation metadata from CrossRef API.
"""
from __future__ import annotations

from bioetl.infrastructure.adapters.crossref.client import (
    CROSSREF_API_BASE,
    CROSSREF_HEALTH_ERRORS,
    CrossRefAdapter,
    CrossRefFetchFlow,
    CrossRefQueryBuilder,
    CrossRefResponseMapper,
)
from bioetl.infrastructure.adapters.crossref.models import (
    CROSSREF_RECORD_MODELS,
    CrossRefPublicationRecord,
    CrossRefPublicationResponse,
    CrossRefPublicationsResponse,
)

__all__ = [
    "CROSSREF_API_BASE",
    "CROSSREF_HEALTH_ERRORS",
    # Model Mappings
    "CROSSREF_RECORD_MODELS",
    # Adapter
    "CrossRefAdapter",
    "CrossRefFetchFlow",
    # Record Models
    "CrossRefPublicationRecord",
    # Response Models
    "CrossRefPublicationResponse",
    "CrossRefPublicationsResponse",
    "CrossRefQueryBuilder",
    "CrossRefResponseMapper",
]
