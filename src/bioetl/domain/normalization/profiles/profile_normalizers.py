"""Shared pure normalizers for normalization profiles."""

from __future__ import annotations

from bioetl.domain.mapping.publication_type_mapping import normalize_publication_type
from bioetl.domain.normalization.chembl import (
    normalize_bao_identifier,
    normalize_cellosaurus_id,
    normalize_chembl_organism_name,
)
from bioetl.domain.normalization.identifiers import (
    normalize_ontology_id,
)
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
)
from bioetl.domain.normalization.rules import (
    normalize_case,
    normalize_null,
    normalize_operator,
    normalize_unit,
)
from bioetl.domain.normalization.text import normalize_string

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
    "normalize_profile_chembl_organism_name",
    "normalize_profile_date",
    "normalize_profile_doi",
    "normalize_profile_enum",
    "normalize_profile_float",
    "normalize_profile_governed_uppercase_vocabulary",
    "normalize_profile_governed_vocabulary",
    "normalize_profile_int",
    "normalize_profile_isomeric_smiles",
    "normalize_profile_json_string",
    "normalize_profile_json_string_list_vocabulary_strict",
    "normalize_profile_json_string_strict",
    "normalize_profile_mapping_status",
    "normalize_profile_null",
    "normalize_profile_ontology_id",
    "normalize_profile_operator",
    "normalize_profile_passthrough",
    "normalize_profile_pmc_id",
    "normalize_profile_pmid",
    "normalize_profile_publication_type",
    "normalize_profile_publication_type_raw",
    "normalize_profile_quasi_enum_numeric",
    "normalize_profile_smiles",
    "normalize_profile_text",
    "normalize_profile_title",
    "normalize_profile_unit",
]


def normalize_profile_null(value: object) -> object:
    """Convert pseudo-null values to proper None in profile fields.

    Args:
        value: The value to check for null patterns

    Returns:
        None if value matches null patterns, original value otherwise
    """
    return normalize_null(value)


def normalize_profile_passthrough(value: object) -> object:
    """Return one profile value unchanged."""
    return value


def normalize_profile_case(
    value: object, *, allowed_values: frozenset[str] | None = None
) -> object:
    """Normalize case for enum-like profile fields.

    Args:
        value: The value to normalize
        allowed_values: Optional set of allowed values for validation

    Returns:
        Normalized uppercase value if valid, None otherwise
    """
    return normalize_case(value, allowed_values)


def normalize_profile_bao_identifier(value: object) -> object:
    """Normalize BAO identifier profile fields to canonical underscore form."""
    if value is None or isinstance(value, str):
        return normalize_bao_identifier(value)
    return value


def normalize_profile_chembl_organism_name(value: object) -> object:
    """Normalize ChEMBL organism display-name fields."""
    if value is None or isinstance(value, str):
        return normalize_chembl_organism_name(value)
    return value


def normalize_profile_operator(
    value: object, *, allowed_values: frozenset[str] | None = None
) -> str | None:
    """Normalize operator-like profile fields to canonical ASCII forms."""
    return normalize_operator(value, allowed_values=allowed_values)


def normalize_profile_ontology_id(value: object) -> object:
    """Normalize ontology identifier fields to canonical prefix form."""
    if not isinstance(value, str):
        return value
    return normalize_ontology_id(value)


def normalize_profile_cellosaurus_id(value: object) -> object:
    """Normalize Cellosaurus identifiers to canonical ``CVCL_XXXX`` form."""
    if value is None or isinstance(value, str):
        return normalize_cellosaurus_id(value)
    return value


def normalize_profile_unit(value: object) -> object:
    """Canonicalize unit strings in profile fields.

    Args:
        value: The unit value to normalize

    Returns:
        Canonical unit string or None if invalid
    """
    return normalize_unit(value)


def normalize_profile_enum(value: object, *, allowed_values: frozenset[str]) -> object:
    """Normalize one enum-like profile field against allowed values.

    Args:
        value: The value to normalize
        allowed_values: Frozenset of allowed enum values

    Returns:
        Normalized value if it's in allowed_values, None otherwise
    """
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
    return candidate if candidate in allowed_values else None


def normalize_profile_quasi_enum_numeric(
    value: object, *, allowed_values: tuple[float, ...]
) -> object:
    """Normalize numeric provider codes while preserving non-integer canonical values."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        cleaned = normalize_string(value)
        if cleaned is None:
            return None
        try:
            numeric = float(cleaned)
        except ValueError:
            return None
    elif isinstance(value, (int, float)):
        numeric = float(value)
    else:
        return None

    if numeric not in allowed_values:
        return None
    return int(numeric) if numeric.is_integer() else numeric


def normalize_profile_assay_parameter_type(
    value: object, *, allowed_values: frozenset[str]
) -> object:
    """Normalize controlled assay-parameter type vocabulary while preserving unknowns."""
    return normalize_profile_governed_uppercase_vocabulary(
        value,
        allowed_values=allowed_values,
        preserve_unknown=True,
    )


def normalize_profile_publication_type(
    value: object,
    *,
    allowed_values: frozenset[str],
) -> object:
    """Normalize publication type through the canonical mapping and enum gate."""
    if not isinstance(value, str):
        return None
    cleaned = normalize_string(value)
    if cleaned is None:
        return None
    normalized = normalize_publication_type(cleaned)
    if normalized is None:
        return None
    return normalized if normalized in allowed_values else None


def normalize_profile_publication_type_raw(value: object) -> object:
    """Normalize raw provider publication-type tokens without mapping to canonical taxonomy."""
    if not isinstance(value, str):
        return None
    cleaned = normalize_string(value)
    return cleaned.upper() if cleaned is not None else None
