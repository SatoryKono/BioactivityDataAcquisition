# ruff: noqa: RUF022
"""Domain schemas for ETL records.

Provides:
- Base Pandera schemas for validation
- Canonical column ordering utilities
- Provider-specific schema definitions
- JSON validators for schema checks
- Centralized constants for schema validation
"""

from __future__ import annotations

from bioetl.domain.schemas.column_order import (
    ALL_SYSTEM_FIELDS,
    DQ_FIELDS_SUFFIX,
    LOOKUP_FIELDS_PREFIX,
    SYSTEM_FIELDS_PREFIX,
    canonical_column_order,
)
from bioetl.domain.schemas.constants import (
    ACTIVITY_STANDARD_TYPES,
    ASSAY_CATEGORIES,
    ASSAY_TEST_TYPES,
    ASSAY_TYPES,
    BAO_ID_PATTERN,
    CELLOSAURUS_ID_PATTERN,
    CHEMBL_ID_PATTERN,
    CLO_ID_PATTERN,
    DATA_VALIDITY_COMMENTS,
    EFO_ID_PATTERN,
    ISO_DATE_PATTERN,
    MAX_PHASE_VALUES,
    MOLECULE_TYPES,
    PUBLICATION_TYPES,
    RELATIONSHIP_TYPES,
    STANDARD_RELATIONS,
    STRUCTURE_TYPES,
    TARGET_COMPONENT_RELATIONSHIPS,
    TARGET_TYPES,
    UO_ID_PATTERN,
)
from bioetl.domain.schemas.validators import (  # Registered check methods (imported for side-effect registration)
    in_closed_range,
    is_non_negative,
    is_positive,
    json_array_check,
    json_check,
    json_object_check,
    max_str_length,
    str_matches_pattern,
    str_starts_with,
)

__all__ = [
    # Column ordering
    "ALL_SYSTEM_FIELDS",
    "DQ_FIELDS_SUFFIX",
    "LOOKUP_FIELDS_PREFIX",
    "SYSTEM_FIELDS_PREFIX",
    "canonical_column_order",
    # JSON validators
    "json_array_check",
    "json_check",
    "json_object_check",
    # Registered check methods
    "in_closed_range",
    "is_non_negative",
    "is_positive",
    "max_str_length",
    "str_matches_pattern",
    "str_starts_with",
    # Regex patterns
    "CHEMBL_ID_PATTERN",
    "BAO_ID_PATTERN",
    "UO_ID_PATTERN",
    "CLO_ID_PATTERN",
    "EFO_ID_PATTERN",
    "CELLOSAURUS_ID_PATTERN",
    "ISO_DATE_PATTERN",
    # Activity enums
    "STANDARD_RELATIONS",
    "ACTIVITY_STANDARD_TYPES",
    "DATA_VALIDITY_COMMENTS",
    # Assay enums
    "ASSAY_TYPES",
    "ASSAY_TEST_TYPES",
    "ASSAY_CATEGORIES",
    "RELATIONSHIP_TYPES",
    # Molecule enums
    "MOLECULE_TYPES",
    "STRUCTURE_TYPES",
    "MAX_PHASE_VALUES",
    # Target enums
    "TARGET_TYPES",
    "TARGET_COMPONENT_RELATIONSHIPS",
    # Publication enums
    "PUBLICATION_TYPES",
]
