"""Normalization profile for the CrossRef Publication Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._publication_classification_rules import (
    publication_classification_rules,
)
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_issn_id,
    normalize_profile_issn_ids,
    normalize_profile_orcid_ids,
)
from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema

__all__ = [
    "CROSSREF_PUBLICATION_PROFILE",
    "CROSSREF_PUBLICATION_SCHEMA_FIELDS",
]

_CROSSREF_PUBLICATION_BASE_FIELDS = tuple(
    PublicationEnrichedSchema.to_schema().columns.keys()
)
_CROSSREF_PUBLICATION_COMPAT_IDENTIFIER_FIELDS = tuple(
    field
    for field in (
        "publication_doi",
        "publication_pmid",
        "publication_pmc_id",
        "_source",
        "issue",
        "volume",
    )
    if field not in _CROSSREF_PUBLICATION_BASE_FIELDS
)
CROSSREF_PUBLICATION_SCHEMA_FIELDS = (
    _CROSSREF_PUBLICATION_BASE_FIELDS + _CROSSREF_PUBLICATION_COMPAT_IDENTIFIER_FIELDS
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
_BOOLEAN_FIELDS = frozenset({"content_domain_crossmark_restriction", "is_oa"})
_SET_LIKE_FIELDS = frozenset(
    {
        "affiliation_list",
        "alternative_id",
        "author_orcids",
        "content_domain_domains",
        "issn_list",
        "subject_keywords",
    }
)
_JSON_STRING_FIELDS = frozenset(
    {
        "affiliation_list",
        "alternative_id",
        "author_details",
        "author_orcids",
        "authors",
        "content_domain_domains",
        "issn_list",
        "references",
    }
)
_SPECIAL_RULES = {
    **publication_classification_rules(),
    "author_orcids": (
        normalize_profile_orcid_ids,
        "Canonicalize ORCID identifiers inside a set-like canonical JSON array.",
    ),
    "issn": (
        normalize_profile_issn_id,
        "Canonicalize ISSN identifier to the shared publication identifier policy.",
    ),
    "issn_electronic": (
        normalize_profile_issn_id,
        "Canonicalize electronic ISSN identifier to the shared publication identifier policy.",
    ),
    "issn_list": (
        normalize_profile_issn_ids,
        "Canonicalize ISSN identifiers inside a set-like canonical JSON array.",
    ),
    "issn_print": (
        normalize_profile_issn_id,
        "Canonicalize print ISSN identifier to the shared publication identifier policy.",
    ),
}

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
    boolean_fields=_BOOLEAN_FIELDS,
    set_like_fields=_SET_LIKE_FIELDS,
    json_string_fields=_JSON_STRING_FIELDS,
    special_rules=_SPECIAL_RULES,
)

CROSSREF_PUBLICATION_PROFILE.assert_covers_schema(CROSSREF_PUBLICATION_SCHEMA_FIELDS)
