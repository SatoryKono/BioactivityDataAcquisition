"""Facade exports for OpenAlex field extraction functions."""

from __future__ import annotations
# ruff: noqa: I001

from bioetl.application.pipelines.openalex._extractors_authors import (
    extract_affiliations as extract_affiliations,
    extract_author_ids as extract_author_ids,
    extract_author_orcids as extract_author_orcids,
    extract_authors as extract_authors,
    extract_institution_country_codes as extract_institution_country_codes,
    extract_institution_ids as extract_institution_ids,
    extract_institution_ror_ids as extract_institution_ror_ids,
)
from bioetl.application.pipelines.openalex._extractors_publication_fields import (
    extract_biblio_info as extract_biblio_info,
    extract_doi as extract_doi,
    extract_external_ids as extract_external_ids,
    extract_journal_info as extract_journal_info,
    extract_keywords as extract_keywords,
    extract_mesh_terms as extract_mesh_terms,
    extract_open_access_info as extract_open_access_info,
    extract_openalex_id as extract_openalex_id,
    reconstruct_abstract as reconstruct_abstract,
)
from bioetl.application.pipelines.openalex._extractors_topics_grants import (
    extract_grants as extract_grants,
    extract_primary_topic as extract_primary_topic,
    extract_topics as extract_topics,
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
