"""Normalization profile for the PubMed Publication Silver schema."""

from __future__ import annotations

from typing import Any

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
    normalize_profile_passthrough,
)
from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema

__all__ = [
    "PUBMED_PUBLICATION_PROFILE",
    "PUBMED_PUBLICATION_SCHEMA_FIELDS",
]


def _pubmed_schema_fields(
    schema_cls: Any,  # Any: Pandera schema classes expose only a runtime `.to_schema()` protocol.
) -> tuple[str, ...]:
    """Return ordered Pandera schema fields for the PubMed publication profile."""
    return tuple(schema_cls.to_schema().columns.keys())


_PUBMED_PUBLICATION_BASE_FIELDS = _pubmed_schema_fields(PubMedPublicationSchema)
_PUBMED_PUBLICATION_COMPAT_IDENTIFIER_FIELDS = tuple(
    field
    for field in (
        "publication_doi",
        "publication_pmid",
        "publication_pmc_id",
        "_source",
        "issue",
        "pub_date",
        "volume",
    )
    if field not in _PUBMED_PUBLICATION_BASE_FIELDS
)
PUBMED_PUBLICATION_SCHEMA_FIELDS = (
    _PUBMED_PUBLICATION_BASE_FIELDS + _PUBMED_PUBLICATION_COMPAT_IDENTIFIER_FIELDS
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
_BOOLEAN_FIELDS = frozenset({"abstract_structured", "is_oa"})
_SET_LIKE_FIELDS = frozenset(
    {
        "affiliation_list",
        "affiliation_structured",
        "affiliation_structured_canonical_json",
        "author_orcids",
        "chemicals",
        "databanks",
        "gene_symbols",
        "issn_list",
        "publication_types",
        "subject_keywords",
        "subject_mesh",
    }
)
_HASH_EXCLUDED_FIELDS = frozenset({"affiliation_structured_raw_json"})
_JSON_STRING_FIELDS = frozenset(
    {
        "affiliation_list",
        "affiliation_structured",
        "affiliation_structured_canonical_json",
        "affiliation_structured_raw_json",
        "author_orcids",
        "authors",
        "authors_with_affiliations",
        "authors_with_affiliations_canonical_json",
        "authors_with_affiliations_raw_json",
        "chemicals",
        "databanks",
        "gene_symbols",
        "issn_list",
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
    "issn_list": (
        normalize_profile_issn_ids,
        "Canonicalize ISSN identifiers inside a set-like canonical JSON array.",
    ),
    "affiliation_structured_raw_json": (
        normalize_profile_passthrough,
        "Preserve the raw provider JSON for structured affiliations.",
    ),
    "authors_with_affiliations_raw_json": (
        normalize_profile_passthrough,
        "Preserve the raw provider JSON for the authors-with-affiliations payload.",
    ),
}

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
    boolean_fields=_BOOLEAN_FIELDS,
    set_like_fields=_SET_LIKE_FIELDS,
    hash_excluded_fields=_HASH_EXCLUDED_FIELDS,
    json_string_fields=_JSON_STRING_FIELDS,
    special_rules=_SPECIAL_RULES,
)

PUBMED_PUBLICATION_PROFILE.assert_covers_schema(PUBMED_PUBLICATION_SCHEMA_FIELDS)
