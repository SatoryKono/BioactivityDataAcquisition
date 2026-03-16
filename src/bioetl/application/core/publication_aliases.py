"""Publication legacy→canonical field alias registry.

Centralizes compatibility aliases used by composite publication pipelines.
Maps ChEMBL API field names to unified canonical names for cross-provider
column ordering and matching.
"""

from __future__ import annotations

__all__ = ["LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE"]


# Explicit deprecation window for legacy publication aliases.
# TODO(RF-008.3): Remove aliases after LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE
LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE = "2026-06-30"

# Legacy aliases declared in publication schema YAML (`field_aliases`).
PUBLICATION_SCHEMA_FIELD_ALIASES: dict[str, str] = {
    "year": "publication_year",
    "first_page": "page_first",
    "last_page": "page_last",
    "doc_type": "publication_type",
    "document_chembl_id": "publication_id",
    "doi": "publication_doi",
    "pmid": "publication_pmid",
    "pmc_id": "publication_pmc_id",
}
