"""CrossRef adapter for publication metadata enrichment.

Provides DOI resolution and citation metadata from CrossRef API.
"""

from bioetl.infrastructure.adapters.crossref.client import (
    CrossRefAdapter,
    _create_crossref_adapter,
)
from bioetl.infrastructure.adapters.crossref.models import (
    CROSSREF_RECORD_MODELS,
    CrossRefPublicationRecord,
    CrossRefPublicationResponse,
    CrossRefPublicationsResponse,
)

__all__ = [
    # Model Mappings
    "CROSSREF_RECORD_MODELS",
    # Adapter
    "CrossRefAdapter",
    # Record Models
    "CrossRefPublicationRecord",
    # Response Models
    "CrossRefPublicationResponse",
    "CrossRefPublicationsResponse",
    "_create_crossref_adapter",
]
