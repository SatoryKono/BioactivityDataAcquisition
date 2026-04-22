"""Normalization profile for the Semantic Scholar Publication Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._publication_classification_rules import (
    publication_classification_rules,
)
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.schemas.semanticscholar.publication import (
    SemanticScholarPublicationSchema,
)

__all__ = [
    "SEMANTICSCHOLAR_PUBLICATION_PROFILE",
    "SEMANTICSCHOLAR_PUBLICATION_SCHEMA_FIELDS",
]

_SEMANTICSCHOLAR_PUBLICATION_BASE_FIELDS = tuple(
    SemanticScholarPublicationSchema.to_schema().columns.keys()
)
_SEMANTICSCHOLAR_PUBLICATION_COMPAT_IDENTIFIER_FIELDS = tuple(
    field
    for field in (
        "publication_doi",
        "publication_pmid",
        "publication_pmc_id",
        "_source",
        "issue",
    )
    if field not in _SEMANTICSCHOLAR_PUBLICATION_BASE_FIELDS
)
SEMANTICSCHOLAR_PUBLICATION_SCHEMA_FIELDS = (
    _SEMANTICSCHOLAR_PUBLICATION_BASE_FIELDS
    + _SEMANTICSCHOLAR_PUBLICATION_COMPAT_IDENTIFIER_FIELDS
)

_META_FIELDS = frozenset(
    {
        "entity_id",
        "content_hash",
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_ingestion_ts",
        "_index",
        "_lookup_method",
        "_original_id",
        "_source",
        "_dq_error",
        "_dq_warn",
    }
)
_TITLE_FIELDS = frozenset({"title"})
_ABSTRACT_FIELDS = frozenset({"abstract", "tldr"})
_DOI_FIELDS = frozenset({"doi", "publication_doi"})
_PMID_FIELDS = frozenset({"pmid", "publication_pmid"})
_PMC_ID_FIELDS = frozenset({"pmc_id", "publication_pmc_id"})
_DATE_FIELDS = frozenset({"publication_date"})
_INT_FIELDS = frozenset(
    {
        "citations_made",
        "citations_received",
        "corpus_id",
        "influential_citation_count",
        "publication_year",
    }
)
_SET_LIKE_FIELDS = frozenset(
    {
        "affiliation_list",
        "author_orcids",
        "author_s2_ids",
        "publication_types",
        "subject_fields",
    }
)
_JSON_STRING_FIELDS = frozenset(
    {
        "affiliation_list",
        "author_h_indices",
        "author_orcids",
        "author_s2_ids",
        "authors",
        "citation_contexts",
        "publication_types",
        "subject_fields",
    }
)

SEMANTICSCHOLAR_PUBLICATION_PROFILE = build_standard_profile(
    profile_name="semanticscholar.publication",
    description="Canonical field-level normalization policy for the Semantic Scholar Publication Silver schema.",
    schema_fields=SEMANTICSCHOLAR_PUBLICATION_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    abstract_fields=_ABSTRACT_FIELDS,
    doi_fields=_DOI_FIELDS,
    pmid_fields=_PMID_FIELDS,
    pmc_id_fields=_PMC_ID_FIELDS,
    date_fields=_DATE_FIELDS,
    int_fields=_INT_FIELDS,
    set_like_fields=_SET_LIKE_FIELDS,
    json_string_fields=_JSON_STRING_FIELDS,
    special_rules=publication_classification_rules(),
)

SEMANTICSCHOLAR_PUBLICATION_PROFILE.assert_covers_schema(
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA_FIELDS
)
