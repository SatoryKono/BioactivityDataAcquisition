"""Shared ChEMBL vocabulary access for normalization profiles."""

from __future__ import annotations

from bioetl.domain.schemas.constants import (
    ACTIVITY_STANDARD_TYPES,
    ACTIVITY_STANDARD_UNITS,
    ASSAY_CATEGORIES,
    ASSAY_GROUPS,
    ASSAY_PARAMETER_STANDARD_TYPES,
    ASSAY_TEST_TYPES,
    ASSAY_TYPES,
    CONFIDENCE_DESCRIPTIONS,
    DATA_VALIDITY_COMMENTS,
    RELATIONSHIP_TYPES,
    STANDARD_RELATIONS,
    SUBCELLULAR_FRACTIONS,
)

__all__ = ["chembl_enum"]

_CHEMBL_ENUMS: dict[tuple[str, str], frozenset[str]] = {
    ("activity", "assay_type"): ASSAY_TYPES,
    ("activity", "data_validity_comment"): DATA_VALIDITY_COMMENTS,
    ("activity", "standard_relation"): STANDARD_RELATIONS,
    ("activity", "standard_type"): ACTIVITY_STANDARD_TYPES,
    ("activity", "standard_units"): ACTIVITY_STANDARD_UNITS,
    ("assay", "assay_category"): ASSAY_CATEGORIES,
    ("assay", "assay_group"): ASSAY_GROUPS,
    ("assay", "assay_test_type"): ASSAY_TEST_TYPES,
    ("assay", "assay_type"): ASSAY_TYPES,
    ("assay", "confidence_description"): CONFIDENCE_DESCRIPTIONS,
    ("assay", "relationship_type"): RELATIONSHIP_TYPES,
    ("assay", "subcellular_fraction"): SUBCELLULAR_FRACTIONS,
    ("assay", "subcellular_fractions"): SUBCELLULAR_FRACTIONS,
    ("assay_parameters", "standard_relation"): STANDARD_RELATIONS,
    ("assay_parameters", "standard_type"): ASSAY_PARAMETER_STANDARD_TYPES,
    ("assay_parameters", "standard_units"): ACTIVITY_STANDARD_UNITS,
}


def chembl_enum(entity: str, field: str) -> frozenset[str]:
    """Return an immutable ChEMBL vocabulary for a profile entity field."""
    key = (entity, field)
    try:
        return _CHEMBL_ENUMS[key]
    except KeyError as exc:
        available = ", ".join(
            f"{known_entity}.{known_field}"
            for known_entity, known_field in sorted(_CHEMBL_ENUMS)
        )
        raise KeyError(
            f"Unknown ChEMBL vocabulary {entity}.{field}; available: {available}"
        ) from exc
