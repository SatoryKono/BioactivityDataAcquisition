"""Publication legacy→canonical field alias registry.

Centralizes compatibility aliases used by composite publication pipelines.
Maps ChEMBL API field names to unified canonical names for cross-provider
column ordering and matching.
"""

from __future__ import annotations

from types import MappingProxyType

LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE = "2026-06-30"
LEGACY_PUBLICATION_FIELD_ALIASES = MappingProxyType(
    {
        "pubmed-id": "publication-pmid",
        "doi": "publication-doi",
        "doc-type": "publication-type",
        "first-page": "page-first",
        "last-page": "page-last",
        "year": "publication-year",
        "document-chembl-id": "publication-id",
        "pmid": "publication-pmid",
        "pmc-id": "publication-pmc-id",
    }
)

__all__ = [
    "LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE",
    "LEGACY_PUBLICATION_FIELD_ALIASES",
]
