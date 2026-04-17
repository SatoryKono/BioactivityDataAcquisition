"""Normalization profile for the ChEMBL Tissue Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.identifiers import normalize_ontology_id
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
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

# Special rules for ontology ID fields
_SPECIAL_RULE_COMPONENTS = {
    "bto_id": (
        normalize_ontology_id,
        "Normalize BTO ontology ID to canonical underscore format.",
    ),
    "caloha_id": (
        normalize_ontology_id,
        "Normalize CALOHA ontology ID to canonical format.",
    ),
    "efo_id": (
        normalize_ontology_id,
        "Normalize EFO ontology ID to canonical underscore format.",
    ),
    "uberon_id": (
        normalize_ontology_id,
        "Normalize UBERON ontology ID to canonical underscore format.",
    ),
}

CHEMBL_TISSUE_PROFILE = build_standard_profile(
    profile_name="chembl.tissue",
    description="Canonical field-level normalization policy for the ChEMBL Tissue Silver schema.",
    schema_fields=CHEMBL_TISSUE_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    special_rules=_SPECIAL_RULE_COMPONENTS,
)

CHEMBL_TISSUE_PROFILE.assert_covers_schema(CHEMBL_TISSUE_SCHEMA_FIELDS)
