"""Normalization profile for the Semantic Scholar Publication Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._publication_classification_rules import (
    publication_classification_rules,
)
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_oa_status,
    normalize_profile_orcid_ids,
    normalize_profile_passthrough,
    normalize_profile_semantic_scholar_id,
    normalize_profile_semantic_scholar_ids,
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
_BOOLEAN_FIELDS = frozenset({"is_oa"})
_SET_LIKE_FIELDS = frozenset(
    {
        "affiliation_list",
        "author_orcids",
        "author_s2_ids",
        "publication_types_canonical_json",
        "publication_types",
        "subject_fields_canonical_json",
        "subject_fields",
    }
)
_JSON_STRING_FIELDS = frozenset(
    {
        "affiliation_list",
        "author_h_indices",
        "author_h_indices_canonical_json",
        "author_h_indices_raw_json",
        "author_orcids",
        "author_s2_ids",
        "authors",
        "citation_contexts",
        "citation_contexts_canonical_json",
        "citation_contexts_raw_json",
        "publication_types_canonical_json",
        "publication_types_raw_json",
        "publication_types",
        "subject_fields_canonical_json",
        "subject_fields_raw_json",
        "subject_fields",
    }
)
_SPECIAL_RULES = {
    **publication_classification_rules(),
    "author_orcids": (
        normalize_profile_orcid_ids,
        "Canonicalize ORCID identifiers inside a set-like canonical JSON array.",
    ),
    "author_s2_ids": (
        normalize_profile_semantic_scholar_ids,
        "Canonicalize Semantic Scholar author identifiers inside a set-like canonical JSON array.",
    ),
    "oa_status": (
        normalize_profile_oa_status,
        "Normalize OA status against the shared publication OA-status registry.",
    ),
    "paper_id": (
        normalize_profile_semantic_scholar_id,
        "Canonicalize Semantic Scholar paper identifier through the shared ID registry.",
    ),
    "author_h_indices_raw_json": (
        normalize_profile_passthrough,
        "Preserve the raw provider JSON for author h-index payloads.",
    ),
    "citation_contexts_raw_json": (
        normalize_profile_passthrough,
        "Preserve the raw provider JSON for citation-context payloads.",
    ),
    "publication_types_raw_json": (
        normalize_profile_passthrough,
        "Preserve the raw provider JSON for publication-type payloads.",
    ),
    "subject_fields_raw_json": (
        normalize_profile_passthrough,
        "Preserve the raw provider JSON for subject-field payloads.",
    ),
}

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
    boolean_fields=_BOOLEAN_FIELDS,
    set_like_fields=_SET_LIKE_FIELDS,
    json_string_fields=_JSON_STRING_FIELDS,
    special_rules=_SPECIAL_RULES,
)

SEMANTICSCHOLAR_PUBLICATION_PROFILE.assert_covers_schema(
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA_FIELDS
)
