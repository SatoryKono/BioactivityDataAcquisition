"""Reusable field blocks for publication-oriented Silver schemas."""

from __future__ import annotations

import pyarrow as pa

from bioetl.infrastructure.schemas.silver_common_field_blocks import (
    build_silver_dq_suffix_fields,
    build_silver_system_prefix_fields,
)


def build_publication_system_prefix_fields() -> list[pa.Field]:
    """Return the canonical system-prefix fields for publication Silver schemas."""
    return build_silver_system_prefix_fields(include_source=True)


def build_publication_dq_suffix_fields() -> list[pa.Field]:
    """Return the canonical DQ suffix fields for publication Silver schemas."""
    return build_silver_dq_suffix_fields()


def build_pubmed_publication_fields() -> list[pa.Field]:
    """Return provider-specific PubMed publication fields."""
    return [
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
        pa.field("abstract", pa.string()),
        pa.field("abstract_structured", pa.bool_()),
        pa.field("affiliation_list", pa.string()),
        pa.field("affiliation_structured", pa.string()),
        pa.field("author_count", pa.int64()),
        pa.field("author_keys", pa.string()),
        pa.field("authors", pa.string()),
        pa.field("authors_with_affiliations", pa.string()),
        pa.field("chemical_count", pa.int64()),
        pa.field("chemicals", pa.string()),
        pa.field("citation_subset", pa.string()),
        pa.field("citations_made", pa.int64()),
        pa.field("country", pa.string()),
        pa.field("databanks", pa.string()),
        pa.field("date_completed", pa.string()),
        pa.field("date_revised", pa.string()),
        pa.field("doi", pa.string()),
        pa.field("gene_symbols", pa.string()),
        pa.field("grant_count", pa.int64()),
        pa.field("issn", pa.string()),
        pa.field("issue", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("journal_iso_abbrev", pa.string()),
        pa.field("journal_issn_type", pa.string()),
        pa.field("journal_name_short", pa.string()),
        pa.field("keyword_count", pa.int64()),
        pa.field("language", pa.string()),
        pa.field("medline_pgn", pa.string()),
        pa.field("mesh_heading_count", pa.int64()),
        pa.field("mid", pa.string()),
        pa.field("nlm_unique_id", pa.string()),
        pa.field("page_first", pa.string()),
        pa.field("page_last", pa.string()),
        pa.field("page_range", pa.string()),
        pa.field("pii", pa.string()),
        pa.field("pmc_id", pa.string()),
        pa.field("pmid", pa.string(), nullable=False),
        pa.field("pub_date", pa.string()),
        pa.field("pub_day", pa.int64()),
        pa.field("pub_month", pa.int64()),
        pa.field("publication_class", pa.string()),
        pa.field("publication_date", pa.string()),
        pa.field("publication_status", pa.string()),
        pa.field("publication_subclass", pa.string()),
        pa.field("publication_type", pa.string()),
        pa.field("publication_type_list", pa.string()),
        pa.field("publication_type_unified", pa.string()),
        pa.field("publication_types", pa.string()),
        pa.field("publication_year", pa.int64()),
        pa.field("publisher_id", pa.string()),
        pa.field("subject_keywords", pa.string()),
        pa.field("subject_mesh", pa.string()),
        pa.field("title", pa.string()),
        pa.field("volume", pa.string()),
    ]


def build_semanticscholar_publication_fields() -> list[pa.Field]:
    """Return provider-specific Semantic Scholar publication fields."""
    return [
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
        pa.field("abstract", pa.string()),
        pa.field("affiliation_list", pa.string()),
        pa.field("author_h_indices", pa.string()),
        pa.field("author_keys", pa.string()),
        pa.field("author_orcids", pa.string()),
        pa.field("author_s2_ids", pa.string()),
        pa.field("authors", pa.string()),
        pa.field("citation_contexts", pa.string()),
        pa.field("citations_made", pa.int64()),
        pa.field("citations_received", pa.int64()),
        pa.field("corpus_id", pa.int64()),
        pa.field("dblp_id", pa.string()),
        pa.field("doi", pa.string()),
        pa.field("influential_citation_count", pa.int64()),
        pa.field("is_oa", pa.bool_()),
        pa.field("issue", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("oa_status", pa.string()),
        pa.field("open_access_url", pa.string()),
        pa.field("page_first", pa.string()),
        pa.field("page_last", pa.string()),
        pa.field("page_range", pa.string()),
        pa.field("paper_id", pa.string(), nullable=False),
        pa.field("pmc_id", pa.string()),
        pa.field("pmid", pa.string()),
        pa.field("publication_class", pa.string()),
        pa.field("publication_date", pa.string()),
        pa.field("publication_subclass", pa.string()),
        pa.field("publication_type", pa.string()),
        pa.field("publication_type_unified", pa.string()),
        pa.field("publication_types", pa.string()),
        pa.field("publication_year", pa.int64()),
        pa.field("subject_fields", pa.string()),
        pa.field("title", pa.string()),
        pa.field("tldr", pa.string()),
        pa.field("volume", pa.string()),
    ]


def build_crossref_publication_fields() -> list[pa.Field]:
    """Return provider-specific CrossRef publication fields."""
    return [
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
        pa.field("abstract", pa.string()),
        pa.field("affiliation_list", pa.string()),
        pa.field("alternative_id", pa.string()),
        pa.field("author_details", pa.string()),
        pa.field("author_keys", pa.string()),
        pa.field("author_orcids", pa.string()),
        pa.field("authors", pa.string()),
        pa.field("citations_made", pa.int64()),
        pa.field("citations_received", pa.int64()),
        pa.field("content_domain_crossmark_restriction", pa.bool_()),
        pa.field("content_domain_domains", pa.string()),
        pa.field("doi", pa.string(), nullable=False),
        pa.field("issn", pa.string()),
        pa.field("issn_electronic", pa.string()),
        pa.field("issn_list", pa.string()),
        pa.field("issn_print", pa.string()),
        pa.field("issue", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("journal_name_short", pa.string()),
        pa.field("language", pa.string()),
        pa.field("license_url", pa.string()),
        pa.field("page_first", pa.string()),
        pa.field("page_last", pa.string()),
        pa.field("pmc_id", pa.string()),
        pa.field("pmid", pa.string()),
        pa.field("publication_class", pa.string()),
        pa.field("publication_date", pa.string()),
        pa.field("publication_subclass", pa.string()),
        pa.field("publication_type", pa.string()),
        pa.field("publication_type_unified", pa.string()),
        pa.field("publication_year", pa.int64()),
        pa.field("published", pa.string()),
        pa.field("published_online", pa.string()),
        pa.field("published_print", pa.string()),
        pa.field("publisher", pa.string()),
        pa.field("references", pa.string()),
        pa.field("subject_keywords", pa.string()),
        pa.field("title", pa.string()),
        pa.field("volume", pa.string()),
    ]


def build_openalex_publication_fields() -> list[pa.Field]:
    """Return provider-specific OpenAlex publication fields."""
    return [
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
        pa.field("abstract", pa.string()),
        pa.field("affiliation_list", pa.string()),
        pa.field("author_keys", pa.string()),
        pa.field("author_openalex_ids", pa.string()),
        pa.field("author_orcids", pa.string()),
        pa.field("authors", pa.string()),
        pa.field("citations_made", pa.int64()),
        pa.field("citations_received", pa.int64()),
        pa.field("doi", pa.string()),
        pa.field("fwci", pa.float64()),
        pa.field("grants", pa.string()),
        pa.field("institution_country_codes", pa.string()),
        pa.field("institution_ids", pa.string()),
        pa.field("is_oa", pa.bool_()),
        pa.field("is_retracted", pa.bool_()),
        pa.field("issn", pa.string()),
        pa.field("issue", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("language", pa.string()),
        pa.field("mag_id", pa.string()),
        pa.field("oa_status", pa.string()),
        pa.field("openalex_id", pa.string(), nullable=False),
        pa.field("page_first", pa.string()),
        pa.field("page_last", pa.string()),
        pa.field("pmc_id", pa.string()),
        pa.field("pmid", pa.string()),
        pa.field("primary_topic", pa.string()),
        pa.field("publication_class", pa.string()),
        pa.field("publication_date", pa.string()),
        pa.field("publication_subclass", pa.string()),
        pa.field("publication_type", pa.string()),
        pa.field("publication_type_unified", pa.string()),
        pa.field("publication_year", pa.int64()),
        pa.field("publisher", pa.string()),
        pa.field("ror_ids", pa.string()),
        pa.field("subject_keywords", pa.string()),
        pa.field("subject_mesh", pa.string()),
        pa.field("subject_topics", pa.string()),
        pa.field("title", pa.string()),
        pa.field("type_crossref", pa.string()),
        pa.field("volume", pa.string()),
    ]


__all__ = [
    "build_crossref_publication_fields",
    "build_openalex_publication_fields",
    "build_publication_dq_suffix_fields",
    "build_publication_system_prefix_fields",
    "build_pubmed_publication_fields",
    "build_semanticscholar_publication_fields",
]
