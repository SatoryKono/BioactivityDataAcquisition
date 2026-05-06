"""Governed enum, unit, and code normalizers shared by schema profiles."""

from __future__ import annotations

from bioetl.domain.normalization.chembl import (
    normalize_qudt_unit as _normalize_qudt_unit,
)
from bioetl.domain.normalization.chembl import (
    normalize_standard_unit as _normalize_standard_unit,
)
from bioetl.domain.normalization.profiles._profile_numeric_normalizers import (
    coerce_profile_quasi_enum_numeric,
)
from bioetl.domain.normalization.profiles._profile_value_normalizers import (
    normalize_profile_governed_uppercase_vocabulary,
    normalize_profile_json_string_list_vocabulary_strict,
)
from bioetl.domain.normalization.rules import normalize_case
from bioetl.domain.normalization.text import normalize_string
from bioetl.domain.schemas.constants import (
    TARGET_COMPONENT_RELATIONSHIPS,
    TARGET_COMPONENT_TYPES,
)

__all__ = [
    "normalize_profile_assay_parameter_type",
    "normalize_profile_enum",
    "normalize_profile_mapping_status",
    "normalize_profile_quasi_enum_numeric",
    "normalize_profile_qudt_unit_reference",
    "normalize_profile_reviewed_flag_code",
    "normalize_profile_standard_unit_enum",
    "normalize_profile_target_component_relationships",
    "normalize_profile_target_component_types",
]


def normalize_profile_standard_unit_enum(
    value: object, *, allowed_values: frozenset[str]
) -> object:
    """Canonicalize one standard-unit field and fail closed outside the enum."""
    if value is None or not isinstance(value, str):
        return None
    normalized = _normalize_standard_unit(value)
    if normalized is None:
        return None
    return normalized if normalized in allowed_values else None


def normalize_profile_qudt_unit_reference(value: object) -> object:
    """Trim one QUDT unit reference token/URI while preserving unknown lexemes."""
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    return _normalize_qudt_unit(value)


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
