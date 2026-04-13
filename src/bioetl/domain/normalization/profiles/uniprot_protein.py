"""Normalization profile for the UniProt Protein Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.schemas.uniprot.protein import UniprotTargetSchema

__all__ = [
    "UNIPROT_PROTEIN_PROFILE",
    "UNIPROT_PROTEIN_SCHEMA_FIELDS",
]

_UNIPROT_PROTEIN_BASE_FIELDS = tuple(UniprotTargetSchema.to_schema().columns.keys())
_UNIPROT_PROTEIN_COMPAT_FIELDS = tuple(
    field
    for field in ("gene_names", "organism_id")
    if field not in _UNIPROT_PROTEIN_BASE_FIELDS
)
UNIPROT_PROTEIN_SCHEMA_FIELDS = (
    _UNIPROT_PROTEIN_BASE_FIELDS + _UNIPROT_PROTEIN_COMPAT_FIELDS
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
        "_dq_error",
        "_dq_warn",
    }
)
_TITLE_FIELDS = frozenset({"protein_name"})
_INT_FIELDS = frozenset({"annotation_score", "organism_id", "sequence_length"})
_SET_LIKE_FIELDS = frozenset({"gene_names"})
_JSON_STRING_FIELDS = frozenset(
    {
        "alternative_products",
        "biophysicochemical_properties",
        "cofactors",
        "features_json",
    }
)

UNIPROT_PROTEIN_PROFILE = build_standard_profile(
    profile_name="uniprot.protein",
    description="Canonical field-level normalization policy for the UniProt Protein Silver schema.",
    schema_fields=UNIPROT_PROTEIN_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
    set_like_fields=_SET_LIKE_FIELDS,
    json_string_fields=_JSON_STRING_FIELDS,
)

UNIPROT_PROTEIN_PROFILE.assert_covers_schema(UNIPROT_PROTEIN_SCHEMA_FIELDS)
