"""Normalization profile for ChEMBL target protein classification relation rows."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.schemas.chembl.target_protein_classification import (
    TargetProteinClassificationSchema,
)

__all__ = [
    "CHEMBL_TARGET_PROTEIN_CLASSIFICATION_PROFILE",
    "CHEMBL_TARGET_PROTEIN_CLASSIFICATION_SCHEMA_FIELDS",
]

CHEMBL_TARGET_PROTEIN_CLASSIFICATION_SCHEMA_FIELDS = tuple(
    TargetProteinClassificationSchema.to_schema().columns.keys()
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
_INT_FIELDS = frozenset(
    {
        "component_id",
        "depth",
        "target_snapshot_row_count",
        "target_component_snapshot_row_count",
        "protein_class_snapshot_row_count",
    }
)
_TITLE_FIELDS = frozenset(
    {
        "l1_name",
        "l2_name",
        "l3_name",
        "l4_name",
        "l5_name",
    }
)

CHEMBL_TARGET_PROTEIN_CLASSIFICATION_PROFILE = build_standard_profile(
    profile_name="chembl.target_protein_classification",
    description=(
        "Canonical normalization policy for derived ChEMBL target "
        "protein-classification Gold relation rows."
    ),
    schema_fields=CHEMBL_TARGET_PROTEIN_CLASSIFICATION_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
    null_fields=chembl_pseudo_null_fields("target_protein_classification"),
    field_rule_overrides={
        "path_ids": {
            "notes": "Trim and collapse blank textual values to None where applicable. JSON pipe-delimited list field.",
            "set_like": True,
        },
        "path_names": {
            "notes": "Trim and collapse blank textual values to None where applicable. JSON pipe-delimited list field.",
            "set_like": True,
        },
        "path_labels": {
            "notes": "Trim and collapse blank textual values to None where applicable. JSON pipe-delimited list field.",
            "set_like": True,
        },
    },
)

CHEMBL_TARGET_PROTEIN_CLASSIFICATION_PROFILE.assert_covers_schema(
    CHEMBL_TARGET_PROTEIN_CLASSIFICATION_SCHEMA_FIELDS
)
