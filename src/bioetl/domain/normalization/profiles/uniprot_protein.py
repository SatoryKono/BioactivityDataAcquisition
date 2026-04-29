"""Normalization profile for the UniProt Protein Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.schemas.uniprot import (
    ENTRY_TYPES,
    PROTEIN_EXISTENCE_LEVELS,
    PROTEIN_FLAGS,
    UniprotTargetSchema,
)

__all__ = [
    "UNIPROT_PROTEIN_PROFILE",
    "UNIPROT_PROTEIN_SCHEMA_FIELDS",
]

_UNIPROT_PROTEIN_BASE_FIELDS = tuple(UniprotTargetSchema.to_schema().columns.keys())
_UNIPROT_PROTEIN_COMPAT_FIELDS = tuple(
    field
    for field in ("gene_names", "organism_id")
    if field not in _UNIPROT_PROTEIN_BASE_FIELDS
)
UNIPROT_PROTEIN_SCHEMA_FIELDS = (
    _UNIPROT_PROTEIN_BASE_FIELDS + _UNIPROT_PROTEIN_COMPAT_FIELDS
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
_TITLE_FIELDS = frozenset({"protein_name"})
_INT_FIELDS = frozenset({"annotation_score", "organism_id", "sequence_length"})
_SET_LIKE_FIELDS = frozenset(
    {
        "cellular_component",
        "chembl_ids",
        "drugbank_ids",
        "gene_names",
        "gene_orf_names",
        "gene_synonyms",
        "go_terms",
        "guidetopharmacology_ids",
        "interpro_xrefs",
        "keywords",
        "molecular_function",
        "pdb_xrefs",
        "pfam_xrefs",
        "reaction_ec_numbers",
        "reactome_xrefs",
        "secondary_accessions",
        "isoform_ids",
        "isoform_names",
        "isoform_synonyms",
        "protein_alternative_names",
        "protein_ec_numbers",
        "protein_short_names",
    }
)
_JSON_STRING_FIELDS = frozenset(
    {
        "alternative_products",
        "biophysicochemical_properties",
        "cellular_component",
        "cofactors",
        "features_json",
        "isoform_ids",
        "isoform_names",
        "isoform_synonyms",
        "lineage",
        "molecular_function",
        "protein_alternative_names",
        "protein_ec_numbers",
        "protein_short_names",
        "reactions",
        "reaction_ec_numbers",
    }
)
_BOOLEAN_FIELDS = frozenset({"reviewed"})
_ENUM_FIELDS = {
    "entry_type": frozenset(ENTRY_TYPES),
    "flag": frozenset(PROTEIN_FLAGS),
    "protein_existence": frozenset(PROTEIN_EXISTENCE_LEVELS),
}

UNIPROT_PROTEIN_PROFILE = build_standard_profile(
    profile_name="uniprot.protein",
    description="Canonical field-level normalization policy for the UniProt Protein Silver schema.",
    schema_fields=UNIPROT_PROTEIN_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
    set_like_fields=_SET_LIKE_FIELDS,
    json_string_fields=_JSON_STRING_FIELDS,
    boolean_fields=_BOOLEAN_FIELDS,
    enum_fields=_ENUM_FIELDS,
)

UNIPROT_PROTEIN_PROFILE.assert_covers_schema(UNIPROT_PROTEIN_SCHEMA_FIELDS)
