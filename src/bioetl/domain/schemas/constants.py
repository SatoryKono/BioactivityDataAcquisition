"""Centralized constants for schema validation.

Regex patterns are defined inline (format-dependent, not DB-version-dependent).
Enum values are loaded from configs/enums/chembl.yaml (single source of truth).

All values are immutable (frozenset/tuple) to prevent accidental modification.

Usage:
    from bioetl.domain.schemas.constants import CHEMBL_ID_PATTERN, ASSAY_TYPES
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

# =============================================================================
# REGEX PATTERNS
# =============================================================================

# ChEMBL identifiers
CHEMBL_ID_PATTERN = r"^CHEMBL\d+$"

# Ontology identifiers
# ChEMBL API returns underscore format (BAO_0000190), not colon format (BAO:0000190)
BAO_ID_PATTERN = r"^BAO[_:]\d+$"  # BioAssay Ontology (accepts both _ and :)
UO_ID_PATTERN = r"^UO[_:]\d+$"  # Units Ontology (accepts both _ and :)
CLO_ID_PATTERN = r"^CLO_\d+$"  # Cell Line Ontology
EFO_ID_PATTERN = r"^EFO_\d+$"  # Experimental Factor Ontology

# External database identifiers
CELLOSAURUS_ID_PATTERN = r"^CVCL_[A-Z0-9]+$"

# Date patterns
ISO_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"

# Publication identifier patterns
ISSN_PATTERN = r"^\d{4}-\d{3}[\dX]$"
ORCID_PATTERN = r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$"

# =============================================================================
# CHEMBL ENUM VALUES (loaded from YAML — single source of truth)
# =============================================================================

_ENUMS_YAML_PATH = Path(__file__).resolve().parents[4] / "configs" / "enums" / "chembl.yaml"


@functools.cache
def _load_chembl_enums() -> dict[str, Any]:
    """Load ChEMBL enum values from YAML config.

    Cached: file is read once per process, reused on subsequent calls.
    """
    with _ENUMS_YAML_PATH.open() as f:
        return yaml.safe_load(f)


def _fs(section: str, key: str) -> frozenset[str]:
    """Load a frozenset[str] from a nested YAML section.key."""
    return frozenset(_load_chembl_enums()[section][key])


def _tup_float(section: str, key: str) -> tuple[float, ...]:
    """Load a tuple[float, ...] from a nested YAML section.key."""
    return tuple(float(v) for v in _load_chembl_enums()[section][key])


# Activity enums
STANDARD_RELATIONS: frozenset[str] = _fs("activity", "standard_relations")
ACTIVITY_STANDARD_TYPES: frozenset[str] = _fs("activity", "standard_types")
DATA_VALIDITY_COMMENTS: frozenset[str] = _fs("activity", "data_validity_comments")

# Assay enums
ASSAY_TYPES: frozenset[str] = _fs("assay", "types")
ASSAY_TEST_TYPES: frozenset[str] = _fs("assay", "test_types")
ASSAY_CATEGORIES: frozenset[str] = _fs("assay", "categories")
RELATIONSHIP_TYPES: frozenset[str] = _fs("assay", "relationship_types")

# Assay parameter standard types (superset of activity types + parameter-specific)
ASSAY_PARAMETER_STANDARD_TYPES: frozenset[str] = (
    ACTIVITY_STANDARD_TYPES | _fs("assay", "parameter_standard_types")
)

# Molecule enums
MOLECULE_TYPES: frozenset[str] = _fs("molecule", "types")
STRUCTURE_TYPES: frozenset[str] = _fs("molecule", "structure_types")
# max_phase uses float for 0.5, so tuple instead of frozenset
MAX_PHASE_VALUES: tuple[float, ...] = _tup_float("molecule", "max_phase_values")

# Target enums
TARGET_TYPES: frozenset[str] = _fs("target", "types")
TARGET_COMPONENT_RELATIONSHIPS: frozenset[str] = _fs("target", "component_relationships")

# Publication enums
PUBLICATION_TYPES: frozenset[str] = _fs("publication", "types")

# =============================================================================
# EXPORTS (for explicit re-export in __init__.py)
# =============================================================================

__all__ = [
    "ACTIVITY_STANDARD_TYPES",
    "ASSAY_CATEGORIES",
    "ASSAY_PARAMETER_STANDARD_TYPES",
    "ASSAY_TEST_TYPES",
    # Assay enums
    "ASSAY_TYPES",
    "BAO_ID_PATTERN",
    "CELLOSAURUS_ID_PATTERN",
    # Regex patterns
    "CHEMBL_ID_PATTERN",
    "CLO_ID_PATTERN",
    "DATA_VALIDITY_COMMENTS",
    "EFO_ID_PATTERN",
    "ISO_DATE_PATTERN",
    "ISSN_PATTERN",
    "MAX_PHASE_VALUES",
    # Molecule enums
    "MOLECULE_TYPES",
    "ORCID_PATTERN",
    # Publication enums
    "PUBLICATION_TYPES",
    "RELATIONSHIP_TYPES",
    # Activity enums
    "STANDARD_RELATIONS",
    "STRUCTURE_TYPES",
    "TARGET_COMPONENT_RELATIONSHIPS",
    # Target enums
    "TARGET_TYPES",
    "UO_ID_PATTERN",
]
