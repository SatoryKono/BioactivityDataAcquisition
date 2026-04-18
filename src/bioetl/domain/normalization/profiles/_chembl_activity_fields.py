"""Field group constants for the ChEMBL activity normalization profile."""

from __future__ import annotations

from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.constants import (
    ACTIVITY_STANDARD_TYPES,
    DATA_VALIDITY_COMMENTS,
    STANDARD_RELATIONS,
)

CHEMBL_ACTIVITY_SCHEMA_FIELDS = tuple(ActivitySchema.to_schema().columns.keys())

# Use enum configurations from centralized constants (loaded from YAML)
# These are already properly loaded and don't require runtime I/O

INT_FIELDS = frozenset(
    {
        "_index",
        "standard_flag",
        "potential_duplicate",
        "manual_curation_flag",
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

# Export enum constants for use in normalization
__all__ = [
    "ACTIVITY_STANDARD_TYPES",
    "CHEMBL_ACTIVITY_SCHEMA_FIELDS",
    "DATA_VALIDITY_COMMENTS",
    "FLOAT_FIELDS",
    "INT_FIELDS",
    "META_FIELDS",
    "SET_LIKE_FIELDS",
    "STANDARD_RELATIONS",
]
