"""Normalization profile for the OpenAlex Publication Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._publication_classification_rules import (
    publication_classification_rules,
)
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_issn_id,
    normalize_profile_oa_status,
    normalize_profile_openalex_author_ids,
    normalize_profile_openalex_institution_ids,
    normalize_profile_openalex_ror_ids,
    normalize_profile_openalex_topic,
    normalize_profile_openalex_topics,
    normalize_profile_openalex_work_id,
    normalize_profile_orcid_ids,
    normalize_profile_passthrough,
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
_BOOLEAN_FIELDS = frozenset({"is_oa", "is_retracted"})
_SET_LIKE_FIELDS = frozenset(
    {
        "affiliation_list",
        "author_openalex_ids",
        "author_orcids",
        "grants",
        "grants_canonical_json",
        "institution_country_codes",
        "institution_ids",
        "primary_topic_canonical_json",
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
        "grants_canonical_json",
        "grants_raw_json",
        "primary_topic",
        "primary_topic_canonical_json",
        "primary_topic_raw_json",
        "ror_ids",
        "subject_topics",
    }
)
_SPECIAL_RULES = {
    **publication_classification_rules(),
    "author_openalex_ids": (
        normalize_profile_openalex_author_ids,
        "Canonicalize OpenAlex author identifiers inside a set-like canonical JSON array.",
    ),
    "author_orcids": (
        normalize_profile_orcid_ids,
        "Canonicalize ORCID identifiers inside a set-like canonical JSON array.",
    ),
    "institution_ids": (
        normalize_profile_openalex_institution_ids,
        "Canonicalize OpenAlex institution identifiers inside a set-like canonical JSON array.",
    ),
    "issn": (
        normalize_profile_issn_id,
        "Canonicalize ISSN identifier to the shared publication identifier policy.",
    ),
    "oa_status": (
        normalize_profile_oa_status,
        "Normalize OA status against the shared publication OA-status registry.",
    ),
    "openalex_id": (
        normalize_profile_openalex_work_id,
        "Canonicalize OpenAlex work identifier through the shared ID registry.",
    ),
    "primary_topic": (
        normalize_profile_openalex_topic,
        "Canonicalize OpenAlex primary-topic reference identifier inside a canonical JSON object.",
    ),
    "primary_topic_raw_json": (
        normalize_profile_passthrough,
        "Preserve the raw provider JSON for the primary-topic payload.",
    ),
    "primary_topic_canonical_json": (
        normalize_profile_openalex_topic,
        "Canonicalize the primary-topic companion JSON payload for semantic-sensitive sidecar storage.",
    ),
    "ror_ids": (
        normalize_profile_openalex_ror_ids,
        "Canonicalize OpenAlex ROR reference identifiers inside a canonical JSON array.",
    ),
    "subject_topics": (
        normalize_profile_openalex_topics,
        "Canonicalize OpenAlex topic reference identifiers inside a canonical JSON array.",
    ),
    "grants_raw_json": (
        normalize_profile_passthrough,
        "Preserve the raw provider JSON for the grants payload.",
    ),
}

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
    boolean_fields=_BOOLEAN_FIELDS,
    set_like_fields=_SET_LIKE_FIELDS,
    json_string_fields=_JSON_STRING_FIELDS,
    special_rules=_SPECIAL_RULES,
)

OPENALEX_PUBLICATION_PROFILE.assert_covers_schema(OPENALEX_PUBLICATION_SCHEMA_FIELDS)
