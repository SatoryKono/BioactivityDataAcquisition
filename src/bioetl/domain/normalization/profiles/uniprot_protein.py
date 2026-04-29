"""Normalization profile for the UniProt Protein Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_chembl_ids,
    normalize_profile_drugbank_ids,
    normalize_profile_pdb_references,
    normalize_profile_pfam_references,
    normalize_profile_reactome_references,
    normalize_profile_uniprot_accessions,
    normalize_profile_uniprot_go_references,
    normalize_profile_uniprot_interpro_references,
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
UNIPROT_PROTEIN_SCHEMA_FIELDS = _UNIPROT_PROTEIN_BASE_FIELDS

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
_INT_FIELDS = frozenset(
    {
        "annotation_score",
        "cross_reference_count",
        "entry_version",
        "feature_count",
        "isoform_count",
        "keyword_count",
        "publication_count",
        "sequence_length",
        "sequence_mass",
        "taxonomy_id",
    }
)
_SET_LIKE_FIELDS = frozenset(
    {
        "cellular_component",
        "chembl_ids",
        "drugbank_ids",
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
_REFERENCE_ID_RULE_NOTES = {
    "go": (
        "Canonicalize UniProt GO reference identifiers inside a canonical JSON "
        "array while preserving companion provider metadata."
    ),
    "interpro": (
        "Canonicalize UniProt InterPro reference identifiers inside a canonical "
        "JSON array while preserving companion provider metadata."
    ),
    "pfam": (
        "Canonicalize UniProt Pfam reference identifiers inside a canonical JSON "
        "array while preserving companion provider metadata."
    ),
    "pdb": (
        "Canonicalize UniProt PDB reference identifiers inside a canonical JSON "
        "array while preserving companion provider metadata."
    ),
    "reactome": (
        "Canonicalize UniProt Reactome reference identifiers inside a canonical "
        "JSON array while preserving companion provider metadata."
    ),
}
_SPECIAL_RULES = {
    "chembl_ids": (
        normalize_profile_chembl_ids,
        "Canonicalize ChEMBL identifiers inside a set-like canonical JSON array.",
    ),
    "cellular_component": (
        normalize_profile_uniprot_go_references,
        _REFERENCE_ID_RULE_NOTES["go"],
    ),
    "drugbank_ids": (
        normalize_profile_drugbank_ids,
        "Canonicalize DrugBank identifiers inside a set-like canonical JSON array.",
    ),
    "go_terms": (
        normalize_profile_uniprot_go_references,
        _REFERENCE_ID_RULE_NOTES["go"],
    ),
    "interpro_xrefs": (
        normalize_profile_uniprot_interpro_references,
        _REFERENCE_ID_RULE_NOTES["interpro"],
    ),
    "molecular_function": (
        normalize_profile_uniprot_go_references,
        _REFERENCE_ID_RULE_NOTES["go"],
    ),
    "pdb_xrefs": (
        normalize_profile_pdb_references,
        _REFERENCE_ID_RULE_NOTES["pdb"],
    ),
    "pfam_xrefs": (
        normalize_profile_pfam_references,
        _REFERENCE_ID_RULE_NOTES["pfam"],
    ),
    "reactome_xrefs": (
        normalize_profile_reactome_references,
        _REFERENCE_ID_RULE_NOTES["reactome"],
    ),
    "secondary_accessions": (
        normalize_profile_uniprot_accessions,
        "Canonicalize UniProt secondary accessions inside a set-like canonical JSON array.",
    ),
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
    special_rules=_SPECIAL_RULES,
)

UNIPROT_PROTEIN_PROFILE.assert_covers_schema(UNIPROT_PROTEIN_SCHEMA_FIELDS)
