"""Centralized constants for schema validation.

Provides regex patterns and enum values used across multiple schemas.
All values are immutable (frozenset/tuple) to prevent accidental modification.

Usage:
    from bioetl.domain.schemas.constants import CHEMBL_ID_PATTERN, ASSAY_TYPES
"""

from __future__ import annotations

# =============================================================================
# REGEX PATTERNS
# =============================================================================

# ChEMBL identifiers
CHEMBL_ID_PATTERN = r"^CHEMBL\d+$"

# Ontology identifiers
BAO_ID_PATTERN = r"^BAO:\d+$"  # BioAssay Ontology
UO_ID_PATTERN = r"^UO:\d+$"  # Units Ontology
CLO_ID_PATTERN = r"^CLO_\d+$"  # Cell Line Ontology
EFO_ID_PATTERN = r"^EFO_\d+$"  # Experimental Factor Ontology

# External database identifiers
CELLOSAURUS_ID_PATTERN = r"^CVCL_[A-Z0-9]+$"

# Date patterns
ISO_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"

# =============================================================================
# CHEMBL ACTIVITY ENUMS
# =============================================================================

STANDARD_RELATIONS: frozenset[str] = frozenset(["=", "<", "<=", ">", ">="])

ACTIVITY_STANDARD_TYPES: frozenset[str] = frozenset(
    [
        "IC50",
        "EC50",
        "Ki",
        "Kd",
        "AC50",
        "GI50",
        "Potency",
        "Inhibition",
        "% Inhibition",
        "Activity",
        "Ratio",
        "ED50",
        "ID50",
    ]
)

DATA_VALIDITY_COMMENTS: frozenset[str] = frozenset(
    [
        "Potential missing data",
        "Potential author error",
        "Manually validated",
        "Potential transcription error",
        "Outside typical range",
        "Non standard unit for type",
        "Author confirmed error",
    ]
)

# =============================================================================
# CHEMBL ASSAY ENUMS
# =============================================================================

ASSAY_TYPES: frozenset[str] = frozenset(["B", "F", "A", "T", "P", "U"])

ASSAY_TEST_TYPES: frozenset[str] = frozenset(["In vivo", "In vitro", "Ex vivo"])

ASSAY_CATEGORIES: frozenset[str] = frozenset(
    [
        "screening",
        "confirmatory",
        "panel",
        "summary",
        "other",
    ]
)

RELATIONSHIP_TYPES: frozenset[str] = frozenset(["D", "H", "M", "N", "S", "U"])

# =============================================================================
# CHEMBL MOLECULE ENUMS
# =============================================================================

MOLECULE_TYPES: frozenset[str] = frozenset(
    [
        "Small molecule",
        "Inorganic small molecule",
        "Polymeric small molecule",
        "Antibody",
        "Antibody drug conjugate",
        "Protein",
        "Oligonucleotide",
        "Oligosaccharide",
        "Cell",
        "Enzyme",
        "Unknown",
        "Unclassified",
    ]
)

STRUCTURE_TYPES: frozenset[str] = frozenset(["MOL", "SEQ", "BOTH", "NONE"])

# max_phase uses float for 0.5, so tuple instead of frozenset
MAX_PHASE_VALUES: tuple[float, ...] = (-1, 0, 0.5, 1, 2, 3, 4)

# =============================================================================
# CHEMBL TARGET ENUMS
# =============================================================================

TARGET_TYPES: frozenset[str] = frozenset(
    [
        "SINGLE PROTEIN",
        "PROTEIN FAMILY",
        "PROTEIN COMPLEX",
        "PROTEIN COMPLEX GROUP",
        "SELECTIVITY GROUP",
        "CHIMERIC PROTEIN",
        "CELL-LINE",
        "TISSUE",
        "ORGANISM",
        "MACROMOLECULE",
        "SMALL MOLECULE",
        "LIPID",
        "METAL",
        "UNKNOWN",
    ]
)

TARGET_COMPONENT_RELATIONSHIPS: frozenset[str] = frozenset(
    [
        "SINGLE PROTEIN",
        "PROTEIN SUBUNIT",
        "RNA",
        "INTERACTING PROTEIN",
    ]
)

# =============================================================================
# CHEMBL PUBLICATION ENUMS
# =============================================================================

PUBLICATION_TYPES: frozenset[str] = frozenset(
    [
        "PUBLICATION",
        "PATENT",
        "DATASET",
        "BOOK",
    ]
)

# =============================================================================
# EXPORTS (for explicit re-export in __init__.py)
# =============================================================================

__all__ = [
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
