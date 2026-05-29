"""Normalization profile for the ChEMBL Publication Silver schema."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.normalization.profiles.chembl_policy_registry import (
    chembl_boolean_family_fields,
)
from bioetl.domain.normalization.profiles._chembl_reference_identifier_rules import (
    chembl_reference_identifier_rules,
)
from bioetl.domain.normalization.profiles._publication_classification_rules import (
    publication_classification_rules,
)
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_issn_id,
    normalize_profile_issn_ids,
    normalize_profile_oa_status,
    normalize_profile_publication_type,
    normalize_profile_publication_type_raw,
)
from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema
from bioetl.domain.schemas.constants import PUBLICATION_TYPES

from .chembl_json_ordering_policy import (
    chembl_json_fields,
    chembl_set_like_json_fields,
)

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
        "publication_type_raw",
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
_SET_LIKE_FIELDS = chembl_set_like_json_fields("chembl_publication")
_STRICT_JSON_FIELDS = chembl_json_fields("chembl_publication")
_BOOLEAN_FIELDS = chembl_boolean_family_fields("bool_like", entity="publication")
_REFERENCE_IDENTIFIER_RULES = chembl_reference_identifier_rules("publication")


def normalize_profile_publication_type_field(
    value: object,
    *,
    record: Mapping[str, object] | None = None,
) -> object:
    return normalize_profile_publication_type(
        value,
        allowed_values=PUBLICATION_TYPES,
        record=record,
    )


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
    strict_json_fields=_STRICT_JSON_FIELDS,
    boolean_fields=_BOOLEAN_FIELDS,
    special_rules={
        **_REFERENCE_IDENTIFIER_RULES,
        **publication_classification_rules(),
        "issn": (
            normalize_profile_issn_id,
            "Canonicalize ISSN identifier to the shared publication identifier policy.",
        ),
        "issn_list": (
            normalize_profile_issn_ids,
            "Canonicalize ISSN identifiers inside a set-like canonical JSON array.",
        ),
        "publication_type_raw": (
            normalize_profile_publication_type_raw,
            "Preserve the raw provider publication type as a provider-native "
            "uppercase token; canonical cross-provider analytical semantics "
            "live in publication_type and publication_type_unified.",
        ),
        "publication_type": (
            normalize_profile_publication_type_field,
            "Normalize raw provider publication type to the canonical "
            "publication enum registry value; raw provider semantics are "
            "retained separately in publication_type_raw.",
        ),
        "oa_status": (
            normalize_profile_oa_status,
            "Normalize oa_status against the reviewed ChEMBL open-access "
            "status strict enum and collapse unknown values to None.",
        ),
    },
    null_fields=chembl_pseudo_null_fields("publication"),
)

CHEMBL_PUBLICATION_PROFILE.assert_covers_schema(CHEMBL_PUBLICATION_SCHEMA_FIELDS)
