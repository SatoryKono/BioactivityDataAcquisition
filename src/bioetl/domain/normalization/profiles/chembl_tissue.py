"""Normalization profile for the ChEMBL Tissue Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.schemas.chembl.tissue import TissueSchema

__all__ = [
    "CHEMBL_TISSUE_PROFILE",
    "CHEMBL_TISSUE_SCHEMA_FIELDS",
]

CHEMBL_TISSUE_SCHEMA_FIELDS = tuple(TissueSchema.to_schema().columns.keys())

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
_TITLE_FIELDS = frozenset({"pref_name"})
_ONTOLOGY_ID_FIELDS = frozenset({"bto_id", "caloha_id", "efo_id", "uberon_id"})

CHEMBL_TISSUE_PROFILE = build_standard_profile(
    profile_name="chembl.tissue",
    description="Canonical field-level normalization policy for the ChEMBL Tissue Silver schema.",
    schema_fields=CHEMBL_TISSUE_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    ontology_id_fields=_ONTOLOGY_ID_FIELDS,
    null_fields=chembl_pseudo_null_fields("tissue"),
)

CHEMBL_TISSUE_PROFILE.assert_covers_schema(CHEMBL_TISSUE_SCHEMA_FIELDS)
