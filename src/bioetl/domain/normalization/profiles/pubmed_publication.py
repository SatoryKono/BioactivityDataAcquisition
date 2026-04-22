"""Normalization profile for the PubMed Publication Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._publication_classification_rules import (
    publication_classification_rules,
)
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema

__all__ = [
    "PUBMED_PUBLICATION_PROFILE",
    "PUBMED_PUBLICATION_SCHEMA_FIELDS",
]

_PUBMED_PUBLICATION_BASE_FIELDS = tuple(
    PubMedPublicationSchema.to_schema().columns.keys()
)
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
_SET_LIKE_FIELDS = frozenset(
    {
        "affiliation_list",
        "affiliation_structured",
        "author_orcids",
        "chemicals",
        "databanks",
        "gene_symbols",
        "publication_type_list",
        "publication_types",
        "subject_keywords",
        "subject_mesh",
    }
)
_JSON_STRING_FIELDS = frozenset(
    {
        "affiliation_list",
        "affiliation_structured",
        "author_orcids",
        "authors",
        "authors_with_affiliations",
        "chemicals",
        "databanks",
        "gene_symbols",
        "publication_type_list",
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
    set_like_fields=_SET_LIKE_FIELDS,
    json_string_fields=_JSON_STRING_FIELDS,
    special_rules=publication_classification_rules(),
)

PUBMED_PUBLICATION_PROFILE.assert_covers_schema(PUBMED_PUBLICATION_SCHEMA_FIELDS)
