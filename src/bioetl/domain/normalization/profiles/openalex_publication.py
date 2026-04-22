"""Normalization profile for the OpenAlex Publication Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles._publication_classification_rules import (
    publication_classification_rules,
)
from bioetl.domain.schemas.openalex.publication import OpenAlexPublicationSchema

__all__ = [
    "OPENALEX_PUBLICATION_PROFILE",
    "OPENALEX_PUBLICATION_SCHEMA_FIELDS",
]

_OPENALEX_PUBLICATION_BASE_FIELDS = tuple(
    OpenAlexPublicationSchema.to_schema().columns.keys()
)
_OPENALEX_PUBLICATION_COMPAT_IDENTIFIER_FIELDS = tuple(
    field
    for field in (
        "publication_doi",
        "publication_pmid",
        "publication_pmc_id",
        "_source",
    )
    if field not in _OPENALEX_PUBLICATION_BASE_FIELDS
)
OPENALEX_PUBLICATION_SCHEMA_FIELDS = (
    _OPENALEX_PUBLICATION_BASE_FIELDS + _OPENALEX_PUBLICATION_COMPAT_IDENTIFIER_FIELDS
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
_ABSTRACT_FIELDS = frozenset({"abstract"})
_DOI_FIELDS = frozenset({"doi", "publication_doi"})
_PMID_FIELDS = frozenset({"pmid", "publication_pmid"})
_PMC_ID_FIELDS = frozenset({"pmc_id", "publication_pmc_id"})
_DATE_FIELDS = frozenset({"publication_date"})
_INT_FIELDS = frozenset({"citations_made", "citations_received", "publication_year"})
_FLOAT_FIELDS = frozenset({"fwci"})
_SET_LIKE_FIELDS = frozenset(
    {
        "affiliation_list",
        "author_openalex_ids",
        "author_orcids",
        "grants",
        "institution_country_codes",
        "institution_ids",
        "ror_ids",
        "subject_keywords",
        "subject_mesh",
        "subject_topics",
    }
)
_JSON_STRING_FIELDS = frozenset(
    {
        "affiliation_list",
        "author_openalex_ids",
        "author_orcids",
        "authors",
        "grants",
        "primary_topic",
        "ror_ids",
        "subject_topics",
    }
)

OPENALEX_PUBLICATION_PROFILE = build_standard_profile(
    profile_name="openalex.publication",
    description="Canonical field-level normalization policy for the OpenAlex Publication Silver schema.",
    schema_fields=OPENALEX_PUBLICATION_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    abstract_fields=_ABSTRACT_FIELDS,
    doi_fields=_DOI_FIELDS,
    pmid_fields=_PMID_FIELDS,
    pmc_id_fields=_PMC_ID_FIELDS,
    date_fields=_DATE_FIELDS,
    int_fields=_INT_FIELDS,
    float_fields=_FLOAT_FIELDS,
    set_like_fields=_SET_LIKE_FIELDS,
    json_string_fields=_JSON_STRING_FIELDS,
    special_rules=publication_classification_rules(),
)

OPENALEX_PUBLICATION_PROFILE.assert_covers_schema(OPENALEX_PUBLICATION_SCHEMA_FIELDS)
