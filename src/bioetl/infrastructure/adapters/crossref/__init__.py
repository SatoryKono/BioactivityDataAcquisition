"""CrossRef adapter for publication metadata enrichment.

Provides DOI resolution and citation metadata from CrossRef API.
"""

from bioetl.infrastructure.adapters.crossref.client import (
    CrossRefAdapter,
    _create_crossref_adapter,
)
from bioetl.infrastructure.adapters.crossref.mappers import WorkToPublicationMapper
from bioetl.infrastructure.adapters.crossref.models import (
    CROSSREF_RECORD_MODELS,
    CrossRefWorkRecord,
    CrossRefWorkResponse,
    CrossRefWorksResponse,
)

__all__ = [
    # Model Mappings
    "CROSSREF_RECORD_MODELS",
    # Adapter
    "CrossRefAdapter",
    # Record Models
    "CrossRefWorkRecord",
    # Response Models
    "CrossRefWorkResponse",
    "CrossRefWorksResponse",
    "WorkToPublicationMapper",
    "_create_crossref_adapter",
]
