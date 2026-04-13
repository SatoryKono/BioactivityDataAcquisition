"""Field group constants for the ChEMBL activity normalization profile."""

from __future__ import annotations

from bioetl.domain.schemas.chembl.activity import ActivitySchema

CHEMBL_ACTIVITY_SCHEMA_FIELDS = tuple(ActivitySchema.to_schema().columns.keys())

INT_FIELDS = frozenset(
    {
        "_index",
        "standard_flag",
        "potential_duplicate",
        "src_id",
        "record_id",
        "publication_year",
    }
)
FLOAT_FIELDS = frozenset(
    {
        "standard_value",
        "pchembl_value",
        "value",
        "upper_value",
        "standard_upper_value",
        "toid",
        "manual_curation_flag",
        "original_activity_id",
        "ligand_efficiency_bei",
        "ligand_efficiency_le",
        "ligand_efficiency_lle",
        "ligand_efficiency_sei",
        "target_taxonomy_id",
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
SET_LIKE_FIELDS = frozenset({"activity_properties"})
