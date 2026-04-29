"""Shared pure normalizers for normalization profiles."""

from __future__ import annotations

from bioetl.domain.normalization.chembl import (
    normalize_bao_identifier,
    normalize_cellosaurus_id,
    normalize_chembl_organism_name,
)
from bioetl.domain.normalization.identifiers import normalize_ontology_id
from bioetl.domain.normalization.profiles._profile_activity_ontology_normalizers import (
    normalize_profile_activity_bao_endpoint_iri,
    normalize_profile_activity_bao_endpoint_mapping_status,
    normalize_profile_activity_bao_format_iri,
    normalize_profile_activity_bao_format_mapping_status,
    normalize_profile_activity_bao_ontology_version,
    normalize_profile_activity_qudt_ontology_version,
    normalize_profile_activity_qudt_unit_iri,
    normalize_profile_activity_qudt_unit_mapping_status,
    normalize_profile_activity_uo_ontology_version,
    normalize_profile_activity_uo_unit_iri,
    normalize_profile_activity_uo_unit_mapping_status,
)
from bioetl.domain.normalization.profiles._profile_numeric_normalizers import (
    coerce_profile_quasi_enum_numeric,
)
from bioetl.domain.normalization.profiles._profile_reference_normalizers import (
    normalize_profile_chembl_id,
    normalize_profile_chembl_ids,
    normalize_profile_drugbank_ids,
    normalize_profile_issn_id,
    normalize_profile_issn_ids,
    normalize_profile_openalex_author_ids,
    normalize_profile_openalex_institution_ids,
    normalize_profile_openalex_ror_ids,
    normalize_profile_openalex_topic,
    normalize_profile_openalex_topics,
    normalize_profile_openalex_work_id,
    normalize_profile_orcid_ids,
    normalize_profile_pdb_references,
    normalize_profile_pfam_references,
    normalize_profile_publication_type,
    normalize_profile_publication_type_raw,
    normalize_profile_reactome_references,
    normalize_profile_semantic_scholar_id,
    normalize_profile_semantic_scholar_ids,
    normalize_profile_uniprot_accession,
    normalize_profile_uniprot_accessions,
    normalize_profile_uniprot_go_references,
    normalize_profile_uniprot_interpro_references,
)
from bioetl.domain.normalization.profiles._profile_textual_normalizers import (
    normalize_profile_abstract,
    normalize_profile_canonical_smiles,
    normalize_profile_date,
    normalize_profile_doi,
    normalize_profile_isomeric_smiles,
    normalize_profile_json_string,
    normalize_profile_json_string_strict,
    normalize_profile_pmc_id,
    normalize_profile_pmid,
    normalize_profile_smiles,
    normalize_profile_text,
    normalize_profile_title,
)
from bioetl.domain.normalization.profiles._profile_value_normalizers import (
    normalize_profile_binary_flag,
    normalize_profile_boolean,
    normalize_profile_float,
    normalize_profile_governed_uppercase_vocabulary,
    normalize_profile_governed_vocabulary,
    normalize_profile_int,
    normalize_profile_json_string_list_vocabulary_strict,
    normalize_profile_oa_status,
)
from bioetl.domain.normalization.rules import (
    normalize_case,
    normalize_null,
    normalize_operator,
    normalize_unit,
)
from bioetl.domain.normalization.text import normalize_string
from bioetl.domain.schemas.constants import (
    TARGET_COMPONENT_RELATIONSHIPS,
    TARGET_COMPONENT_TYPES,
)

__all__ = [
    "normalize_profile_abstract",
    "normalize_profile_activity_bao_endpoint_iri",
    "normalize_profile_activity_bao_endpoint_mapping_status",
    "normalize_profile_activity_bao_format_iri",
    "normalize_profile_activity_bao_format_mapping_status",
    "normalize_profile_activity_bao_ontology_version",
    "normalize_profile_activity_qudt_ontology_version",
    "normalize_profile_activity_qudt_unit_iri",
    "normalize_profile_activity_qudt_unit_mapping_status",
    "normalize_profile_activity_uo_ontology_version",
    "normalize_profile_activity_uo_unit_iri",
    "normalize_profile_activity_uo_unit_mapping_status",
    "normalize_profile_assay_parameter_type",
    "normalize_profile_bao_identifier",
    "normalize_profile_binary_flag",
    "normalize_profile_boolean",
    "normalize_profile_canonical_smiles",
    "normalize_profile_case",
    "normalize_profile_cellosaurus_id",
    "normalize_profile_chembl_id",
    "normalize_profile_chembl_ids",
    "normalize_profile_chembl_organism_name",
    "normalize_profile_date",
    "normalize_profile_doi",
    "normalize_profile_drugbank_ids",
    "normalize_profile_enum",
    "normalize_profile_float",
    "normalize_profile_governed_uppercase_vocabulary",
    "normalize_profile_governed_vocabulary",
    "normalize_profile_int",
    "normalize_profile_isomeric_smiles",
    "normalize_profile_issn_id",
    "normalize_profile_issn_ids",
    "normalize_profile_json_string",
    "normalize_profile_json_string_list_vocabulary_strict",
    "normalize_profile_json_string_strict",
    "normalize_profile_mapping_status",
    "normalize_profile_null",
    "normalize_profile_oa_status",
    "normalize_profile_ontology_id",
    "normalize_profile_openalex_author_ids",
    "normalize_profile_openalex_institution_ids",
    "normalize_profile_openalex_ror_ids",
    "normalize_profile_openalex_topic",
    "normalize_profile_openalex_topics",
    "normalize_profile_openalex_work_id",
    "normalize_profile_operator",
    "normalize_profile_orcid_ids",
    "normalize_profile_passthrough",
    "normalize_profile_pdb_references",
    "normalize_profile_pfam_references",
    "normalize_profile_pmc_id",
    "normalize_profile_pmid",
    "normalize_profile_publication_type",
    "normalize_profile_publication_type_raw",
    "normalize_profile_quasi_enum_numeric",
    "normalize_profile_reactome_references",
    "normalize_profile_reviewed_flag_code",
    "normalize_profile_semantic_scholar_id",
    "normalize_profile_semantic_scholar_ids",
    "normalize_profile_smiles",
    "normalize_profile_target_component_relationships",
    "normalize_profile_target_component_types",
    "normalize_profile_text",
    "normalize_profile_title",
    "normalize_profile_uniprot_accession",
    "normalize_profile_uniprot_accessions",
    "normalize_profile_uniprot_go_references",
    "normalize_profile_uniprot_interpro_references",
    "normalize_profile_unit",
]


def normalize_profile_null(value: object) -> object:
    """Convert profile pseudo-null values to ``None``."""
    return normalize_null(value)


def normalize_profile_passthrough(value: object) -> object:
    """Return one profile value unchanged."""
    return value


def normalize_profile_case(
    value: object, *, allowed_values: frozenset[str] | None = None
) -> object:
    """Normalize case for enum-like profile fields."""
    return normalize_case(value, allowed_values)


def normalize_profile_bao_identifier(value: object) -> object:
    """Normalize BAO identifier profile fields to canonical underscore form."""
    return (
        normalize_bao_identifier(value)
        if value is None or isinstance(value, str)
        else value
    )


def normalize_profile_chembl_organism_name(value: object) -> object:
    """Normalize ChEMBL organism display-name fields."""
    return (
        normalize_chembl_organism_name(value)
        if value is None or isinstance(value, str)
        else value
    )


def normalize_profile_operator(
    value: object, *, allowed_values: frozenset[str] | None = None
) -> str | None:
    """Normalize operator-like profile fields to canonical ASCII forms."""
    return normalize_operator(value, allowed_values=allowed_values)


def normalize_profile_ontology_id(value: object) -> object:
    """Normalize ontology identifier fields to canonical prefix form."""
    return normalize_ontology_id(value) if isinstance(value, str) else value


def normalize_profile_cellosaurus_id(value: object) -> object:
    """Normalize Cellosaurus identifiers to canonical ``CVCL_XXXX`` form."""
    return (
        normalize_cellosaurus_id(value)
        if value is None or isinstance(value, str)
        else value
    )


def normalize_profile_unit(value: object) -> object:
    """Canonicalize unit strings in profile fields."""
    return normalize_unit(value)


def normalize_profile_enum(value: object, *, allowed_values: frozenset[str]) -> object:
    """Normalize one enum-like profile field against allowed values."""
    if value is None:
        return None
    if isinstance(value, str):
        return normalize_case(value, allowed_values)
    return value if value in allowed_values else None


def normalize_profile_mapping_status(
    value: object, *, allowed_values: frozenset[str]
) -> object:
    """Normalize mapping-status companion fields to canonical lowercase enums."""
    if not isinstance(value, str):
        return None
    cleaned = normalize_string(value)
    if cleaned is None:
        return None
    candidate = cleaned.casefold()
    if candidate not in allowed_values:
        return None
    return candidate


def normalize_profile_quasi_enum_numeric(
    value: object, *, allowed_values: tuple[float, ...]
) -> object:
    """Normalize numeric provider codes while preserving non-integer canonical values."""
    numeric = coerce_profile_quasi_enum_numeric(value)
    if numeric is None or numeric not in allowed_values:
        return None
    return int(numeric) if numeric.is_integer() else numeric


def normalize_profile_reviewed_flag_code(
    value: object,
    *,
    allowed_values: tuple[float, ...] = (-1.0, 0.0, 1.0),
) -> object:
    """Normalize reviewed flag-like provider codes with tri-state semantics."""
    return normalize_profile_quasi_enum_numeric(value, allowed_values=allowed_values)


def normalize_profile_assay_parameter_type(
    value: object, *, allowed_values: frozenset[str]
) -> object:
    """Normalize controlled assay-parameter type vocabulary while preserving unknowns."""
    return normalize_profile_governed_uppercase_vocabulary(
        value,
        allowed_values=allowed_values,
        preserve_unknown=True,
    )


def normalize_profile_target_component_types(value: object) -> object:
    """Normalize target component-type arrays through the strict JSON vocab seam."""
    return normalize_profile_json_string_list_vocabulary_strict(
        value,
        allowed_values=TARGET_COMPONENT_TYPES,
    )


def normalize_profile_target_component_relationships(value: object) -> object:
    """Normalize target component-relationship arrays through the strict JSON seam."""
    return normalize_profile_json_string_list_vocabulary_strict(
        value,
        allowed_values=TARGET_COMPONENT_RELATIONSHIPS,
    )
