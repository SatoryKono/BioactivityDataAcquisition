"""Normalization profile for the ChEMBL Cell Line Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_cellosaurus_id,
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
_ONTOLOGY_ID_FIELDS = frozenset({"clo_id", "efo_id"})
_SPECIAL_RULES = {
    "cellosaurus_id": (
        normalize_profile_cellosaurus_id,
        "Normalize Cellosaurus identifiers to canonical CVCL-prefixed form.",
    )
}

CHEMBL_CELL_LINE_PROFILE = build_standard_profile(
    profile_name="chembl.cell_line",
    description="Canonical field-level normalization policy for the ChEMBL Cell Line Silver schema.",
    schema_fields=CHEMBL_CELL_LINE_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
    ontology_id_fields=_ONTOLOGY_ID_FIELDS,
    special_rules=_SPECIAL_RULES,
    null_fields=chembl_pseudo_null_fields("cell_line"),
)

CHEMBL_CELL_LINE_PROFILE.assert_covers_schema(CHEMBL_CELL_LINE_SCHEMA_FIELDS)
