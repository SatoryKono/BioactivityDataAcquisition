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
    CHEMBL_ENUM_CATALOG,
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
from bioetl.domain.schemas.validators import (
    JSON_ARRAY_CHECK,
    JSON_CHECK,
    JSON_OBJECT_CHECK,
    # Registered check methods (imported for side-effect registration)
    in_closed_range,
    is_non_negative,
    is_positive,
    max_str_length,
    str_matches_pattern,
    str_starts_with,
)

__all__ = [
    "ACTIVITY_STANDARD_TYPES",
    "ALL_SYSTEM_FIELDS",
    "ASSAY_CATEGORIES",
    "ASSAY_TEST_TYPES",
    "ASSAY_TYPES",
    "BAO_ID_PATTERN",
    "CELLOSAURUS_ID_PATTERN",
    "CHEMBL_ENUM_CATALOG",
    "CHEMBL_ID_PATTERN",
    "CLO_ID_PATTERN",
    "DATA_VALIDITY_COMMENTS",
    "DQ_FIELDS_SUFFIX",
    "EFO_ID_PATTERN",
    "ISO_DATE_PATTERN",
    "JSON_ARRAY_CHECK",
    "JSON_CHECK",
    "JSON_OBJECT_CHECK",
    "LOOKUP_FIELDS_PREFIX",
    "MAX_PHASE_VALUES",
    "MOLECULE_TYPES",
    "PUBLICATION_TYPES",
    "RELATIONSHIP_TYPES",
    "STANDARD_RELATIONS",
    "STRUCTURE_TYPES",
    "SYSTEM_FIELDS_PREFIX",
    "TARGET_COMPONENT_RELATIONSHIPS",
    "TARGET_TYPES",
    "UO_ID_PATTERN",
    "canonical_column_order",
    "in_closed_range",
    "is_non_negative",
    "is_positive",
    "max_str_length",
    "str_matches_pattern",
    "str_starts_with",
]
