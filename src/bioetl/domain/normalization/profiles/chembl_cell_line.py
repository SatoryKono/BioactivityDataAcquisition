"""Normalization profile for the ChEMBL Cell Line Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.identifiers import normalize_ontology_id
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.schemas.chembl.cell_line import CellLineSchema

__all__ = [
    "CHEMBL_CELL_LINE_PROFILE",
    "CHEMBL_CELL_LINE_SCHEMA_FIELDS",
]

CHEMBL_CELL_LINE_SCHEMA_FIELDS = tuple(CellLineSchema.to_schema().columns.keys())

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
_TITLE_FIELDS = frozenset({"cell_name", "cell_source_tissue"})
_INT_FIELDS = frozenset({"cell_source_taxonomy_id"})

# Special rules for ontology ID fields
_SPECIAL_RULE_COMPONENTS = {
    "clo_id": (
        normalize_ontology_id,
        "Normalize CLO ontology ID to canonical underscore format.",
    ),
    "efo_id": (
        normalize_ontology_id,
        "Normalize EFO ontology ID to canonical underscore format.",
    ),
}

CHEMBL_CELL_LINE_PROFILE = build_standard_profile(
    profile_name="chembl.cell_line",
    description="Canonical field-level normalization policy for the ChEMBL Cell Line Silver schema.",
    schema_fields=CHEMBL_CELL_LINE_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
    special_rules=_SPECIAL_RULE_COMPONENTS,
    null_fields=chembl_pseudo_null_fields("cell_line"),
)

CHEMBL_CELL_LINE_PROFILE.assert_covers_schema(CHEMBL_CELL_LINE_SCHEMA_FIELDS)
