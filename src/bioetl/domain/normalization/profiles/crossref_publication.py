"""Normalization profile for the CrossRef Publication Silver schema."""

from __future__ import annotations

from ._standard_profile_builder import build_standard_profile

__all__ = [
    "CROSSREF_PUBLICATION_PROFILE",
    "CROSSREF_PUBLICATION_SCHEMA_FIELDS",
]

CROSSREF_PUBLICATION_SCHEMA_FIELDS = (
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
    "affiliation_list",
    "alternative_id",
    "author_details",
    "author_keys",
    "author_orcids",
    "authors",
    "citations_made",
    "citations_received",
    "content_domain_crossmark_restriction",
    "content_domain_domains",
    "doi",
    "issn",
    "issn_electronic",
    "issn_list",
    "issn_print",
    "issue",
    "journal",
    "journal_name_short",
    "language",
    "license_url",
    "page_first",
    "page_last",
    "pmc_id",
    "pmid",
    "publication_class",
    "publication_date",
    "publication_subclass",
    "publication_type",
    "publication_type_unified",
    "publication_year",
    "published",
    "published_online",
    "published_print",
    "publisher",
    "references",
    "subject_keywords",
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
        "publication_date",
        "published",
        "published_online",
        "published_print",
    }
)
_INT_FIELDS = frozenset(
    {
        "citations_made",
        "citations_received",
        "publication_year",
    }
)

CROSSREF_PUBLICATION_PROFILE = build_standard_profile(
    profile_name="crossref.publication",
    description="Canonical field-level normalization policy for the CrossRef Publication Silver schema.",
    schema_fields=CROSSREF_PUBLICATION_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    abstract_fields=_ABSTRACT_FIELDS,
    doi_fields=_DOI_FIELDS,
    pmid_fields=_PMID_FIELDS,
    pmc_id_fields=_PMC_ID_FIELDS,
    date_fields=_DATE_FIELDS,
    int_fields=_INT_FIELDS,
)

CROSSREF_PUBLICATION_PROFILE.assert_covers_schema(CROSSREF_PUBLICATION_SCHEMA_FIELDS)
