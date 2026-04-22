"""Normalization profile for the ChEMBL Publication Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema

__all__ = [
    "CHEMBL_PUBLICATION_PROFILE",
    "CHEMBL_PUBLICATION_SCHEMA_FIELDS",
]

_CHEMBL_PUBLICATION_BASE_FIELDS = tuple(
    ChemblPublicationSchema.to_schema().columns.keys()
)
_CHEMBL_PUBLICATION_COMPAT_IDENTIFIER_FIELDS = tuple(
    field
    for field in (
        "publication_doi",
        "publication_pmid",
        "publication_pmc_id",
        "oa_status",
        "_source",
    )
    if field not in _CHEMBL_PUBLICATION_BASE_FIELDS
)
CHEMBL_PUBLICATION_SCHEMA_FIELDS = (
    _CHEMBL_PUBLICATION_BASE_FIELDS + _CHEMBL_PUBLICATION_COMPAT_IDENTIFIER_FIELDS
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
_DATE_FIELDS = frozenset({"publication_date", "creation_date"})
_INT_FIELDS = frozenset(
    {"publication_year", "src_id", "citations_received", "citations_made"}
)
_SET_LIKE_FIELDS = frozenset({"affiliation_list", "author_orcids"})
_JSON_STRING_FIELDS = frozenset({"authors", "affiliation_list", "author_orcids"})

CHEMBL_PUBLICATION_PROFILE = build_standard_profile(
    profile_name="chembl.publication",
    description="Canonical field-level normalization policy for the ChEMBL Publication Silver schema.",
    schema_fields=CHEMBL_PUBLICATION_SCHEMA_FIELDS,
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
    null_fields=chembl_pseudo_null_fields("publication"),
)

CHEMBL_PUBLICATION_PROFILE.assert_covers_schema(CHEMBL_PUBLICATION_SCHEMA_FIELDS)
