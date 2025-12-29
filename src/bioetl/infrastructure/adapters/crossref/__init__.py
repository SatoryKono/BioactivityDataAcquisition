"""CrossRef adapter for publication metadata enrichment.

Provides DOI resolution and citation metadata from CrossRef API.
"""

from bioetl.infrastructure.adapters.crossref.client import (
    CrossRefAdapter,
    _create_crossref_adapter,
)
from bioetl.infrastructure.adapters.crossref.mappers import WorkToPublicationMapper

__all__ = [
    "CrossRefAdapter",
    "WorkToPublicationMapper",
    "_create_crossref_adapter",
]
