"""Normalization profile for the PubMed Publication Silver schema."""

from __future__ import annotations

from ._standard_profile_builder import build_standard_profile

__all__ = [
    "PUBMED_PUBLICATION_PROFILE",
    "PUBMED_PUBLICATION_SCHEMA_FIELDS",
]

PUBMED_PUBLICATION_SCHEMA_FIELDS = (
    "entity_id",
    "content_hash",
    "_run_id",
    "_run_type",
    "_source_batch_id",
    "_source",
    "_ingestion_ts",
    "_index",
    "_lookup_method",
    "_original_id",
    "abstract",
    "abstract_structured",
    "affiliation_list",
    "affiliation_structured",
    "author_count",
    "author_keys",
    "authors",
    "authors_with_affiliations",
    "chemical_count",
    "chemicals",
    "citation_subset",
    "citations_made",
    "country",
    "databanks",
    "date_completed",
    "date_revised",
    "doi",
    "gene_symbols",
    "grant_count",
    "issn",
    "issue",
    "journal",
    "journal_iso_abbrev",
    "journal_issn_type",
    "journal_name_short",
    "keyword_count",
    "language",
    "medline_pgn",
    "mesh_heading_count",
    "mid",
    "nlm_unique_id",
    "page_first",
    "page_last",
    "page_range",
    "pii",
    "pmc_id",
    "pmid",
    "pub_date",
    "pub_day",
    "pub_month",
    "publication_class",
    "publication_date",
    "publication_status",
    "publication_subclass",
    "publication_type",
    "publication_type_list",
    "publication_type_unified",
    "publication_types",
    "publication_year",
    "publisher_id",
    "subject_keywords",
    "subject_mesh",
    "title",
    "volume",
    "_dq_error",
    "_dq_warn",
)

_META_FIELDS = frozenset(
    {
        "entity_id",
        "content_hash",
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_source",
        "_ingestion_ts",
        "_index",
        "_lookup_method",
        "_original_id",
        "_dq_error",
        "_dq_warn",
    }
)
_TITLE_FIELDS = frozenset({"title"})
_ABSTRACT_FIELDS = frozenset({"abstract"})
_DOI_FIELDS = frozenset({"doi"})
_PMID_FIELDS = frozenset({"pmid"})
_PMC_ID_FIELDS = frozenset({"pmc_id"})
_DATE_FIELDS = frozenset(
    {
        "date_completed",
        "date_revised",
        "pub_date",
        "publication_date",
    }
)
_INT_FIELDS = frozenset(
    {
        "author_count",
        "chemical_count",
        "citations_made",
        "grant_count",
        "keyword_count",
        "mesh_heading_count",
        "pub_day",
        "pub_month",
        "publication_year",
    }
)

PUBMED_PUBLICATION_PROFILE = build_standard_profile(
    profile_name="pubmed.publication",
    description="Canonical field-level normalization policy for the PubMed Publication Silver schema.",
    schema_fields=PUBMED_PUBLICATION_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    abstract_fields=_ABSTRACT_FIELDS,
    doi_fields=_DOI_FIELDS,
    pmid_fields=_PMID_FIELDS,
    pmc_id_fields=_PMC_ID_FIELDS,
    date_fields=_DATE_FIELDS,
    int_fields=_INT_FIELDS,
)

PUBMED_PUBLICATION_PROFILE.assert_covers_schema(PUBMED_PUBLICATION_SCHEMA_FIELDS)
