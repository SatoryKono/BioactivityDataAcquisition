"""Normalization profile for the ChEMBL Protein Class Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.schemas.chembl.protein_classification import (
    ProteinClassificationSchema,
)

__all__ = [
    "CHEMBL_PROTEIN_CLASS_PROFILE",
    "CHEMBL_PROTEIN_CLASS_SCHEMA_FIELDS",
]

CHEMBL_PROTEIN_CLASS_SCHEMA_FIELDS = tuple(
    ProteinClassificationSchema.to_schema().columns.keys()
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
_TITLE_FIELDS = frozenset({"pref_name", "short_name"})
_INT_FIELDS = frozenset(
    {
        "protein_class_id",
        "parent_id",
        "replaced_by",
        "class_level",
        "sort_order",
        "downgraded",
    }
)

CHEMBL_PROTEIN_CLASS_PROFILE = build_standard_profile(
    profile_name="chembl.protein_class",
    description="Canonical field-level normalization policy for the ChEMBL Protein Class Silver schema.",
    schema_fields=CHEMBL_PROTEIN_CLASS_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
)

CHEMBL_PROTEIN_CLASS_PROFILE.assert_covers_schema(CHEMBL_PROTEIN_CLASS_SCHEMA_FIELDS)
