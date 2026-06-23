"""Field group constants for the ChEMBL activity normalization profile."""

from __future__ import annotations

from bioetl.domain.schemas.chembl.activity import ActivitySchema

from ._chembl_vocab import chembl_enum
from .chembl_json_ordering_policy import chembl_set_like_json_fields

CHEMBL_ACTIVITY_SCHEMA_FIELDS = tuple(ActivitySchema.to_schema().columns.keys())

ACTIVITY_ACTION_TYPES = chembl_enum("activity", "action_type")
ACTIVITY_STANDARD_TYPES = chembl_enum("activity", "standard_type")
ACTIVITY_STANDARD_UNITS = chembl_enum("activity", "standard_units")
ASSAY_TYPES = chembl_enum("activity", "assay_type")
DATA_VALIDITY_COMMENTS = chembl_enum("activity", "data_validity_comment")
STANDARD_RELATIONS = chembl_enum("activity", "standard_relation")

INT_FIELDS = frozenset(
    {
        "_index",
        "standard_flag",
        "potential_duplicate",
        "manual_curation_flag",
        "src_id",
        "record_id",
        "publication_year",
        "target_taxonomy_id",
    }
)
FLOAT_FIELDS = frozenset(
    {
        "standard_value",
        "pchembl_value",
        "activity_value",
        "upper_value",
        "standard_upper_value",
        "toid",
        "original_activity_id",
        "ligand_efficiency_bei",
        "ligand_efficiency_le",
        "ligand_efficiency_lle",
        "ligand_efficiency_sei",
    }
)
META_FIELDS = frozenset(
    {
        "entity_id",
        "content_hash",
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_ingestion_ts",
        "_index",
        "_dq_warn",
        "_dq_error",
        "_state",
    }
)
SET_LIKE_FIELDS = chembl_set_like_json_fields("chembl_activity")

# Export enum constants for use in normalization
__all__ = [
    "ACTIVITY_ACTION_TYPES",
    "ACTIVITY_STANDARD_TYPES",
    "ACTIVITY_STANDARD_UNITS",
    "ASSAY_TYPES",
    "CHEMBL_ACTIVITY_SCHEMA_FIELDS",
    "DATA_VALIDITY_COMMENTS",
    "FLOAT_FIELDS",
    "INT_FIELDS",
    "META_FIELDS",
    "SET_LIKE_FIELDS",
    "STANDARD_RELATIONS",
]
