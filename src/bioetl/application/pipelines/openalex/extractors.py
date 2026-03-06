"""Facade exports for OpenAlex field extraction functions."""

from __future__ import annotations

from bioetl.application.pipelines.openalex._extractors_authors import (
    extract_affiliations,
    extract_author_ids,
    extract_author_orcids,
    extract_authors,
    extract_institution_country_codes,
    extract_institution_ids,
    extract_institution_ror_ids,
)
from bioetl.application.pipelines.openalex._extractors_publication_fields import (
    extract_biblio_info,
    extract_doi,
    extract_external_ids,
    extract_journal_info,
    extract_keywords,
    extract_mesh_terms,
    extract_open_access_info,
    extract_openalex_id,
    reconstruct_abstract,
)
from bioetl.application.pipelines.openalex._extractors_topics_grants import (
    extract_grants,
    extract_primary_topic,
    extract_topics,
)

__all__ = [
    "extract_affiliations",
    "extract_author_ids",
    "extract_author_orcids",
    "extract_authors",
    "extract_biblio_info",
    "extract_doi",
    "extract_external_ids",
    "extract_grants",
    "extract_institution_country_codes",
    "extract_institution_ids",
    "extract_institution_ror_ids",
    "extract_journal_info",
    "extract_keywords",
    "extract_mesh_terms",
    "extract_open_access_info",
    "extract_openalex_id",
    "extract_primary_topic",
    "extract_topics",
    "reconstruct_abstract",
]
