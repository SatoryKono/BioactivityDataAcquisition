"""Field group constants for the ChEMBL activity normalization profile."""

from __future__ import annotations

from bioetl.domain.schemas.chembl.activity import ActivitySchema

CHEMBL_ACTIVITY_SCHEMA_FIELDS = tuple(ActivitySchema.to_schema().columns.keys())

TEXT_FIELDS = frozenset(
    {
        "entity_id",
        "content_hash",
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_ingestion_ts",
        "_state",
        "activity_id",
        "assay_id",
        "molecule_id",
        "target_id",
        "publication_id",
        "standard_relation",
        "standard_units",
        "standard_type",
        "data_validity_comment",
        "activity_comment",
        "bao_endpoint",
        "uo_units",
        "qudt_units",
        "type",
        "relation",
        "units",
        "text_value",
        "standard_text_value",
        "data_validity_description",
        "action_type",
        "action_type_description",
        "action_type_parent_type",
        "canonical_smiles",
        "molecule_pref_name",
        "parent_molecule_id",
        "target_pref_name",
        "target_organism",
        "assay_type",
        "assay_description",
        "assay_variant_accession",
        "assay_variant_mutation",
        "bao_format",
        "bao_label",
        "journal",
    }
)
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
