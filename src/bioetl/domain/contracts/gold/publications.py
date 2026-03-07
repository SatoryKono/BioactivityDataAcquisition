"""Publication Gold layer data contracts facade."""

from __future__ import annotations

from bioetl.domain.contracts.gold.publications_crossref import (
    CrossRefPublicationGoldSchema,
)
from bioetl.domain.contracts.gold.publications_openalex import (
    OpenAlexPublicationGoldSchema,
)
from bioetl.domain.contracts.gold.publications_pubmed import PubMedPublicationGoldSchema
from bioetl.domain.contracts.gold.publications_semanticscholar import (
    SemanticScholarPublicationGoldSchema,
)

__all__ = [
    "CrossRefPublicationGoldSchema",
    "OpenAlexPublicationGoldSchema",
    "PubMedPublicationGoldSchema",
    "SemanticScholarPublicationGoldSchema",
]
