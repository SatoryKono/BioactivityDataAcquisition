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

# Assay parameter standard types (superset of activity types + parameter-specific)
ASSAY_PARAMETER_STANDARD_TYPES: frozenset[str] = frozenset(
    [
        # Measurement types (from ACTIVITY_STANDARD_TYPES)
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
        # Parameter-specific types
        "CONC",  # Concentration
        "PH",  # pH level
        "TEMP",  # Temperature
        "TIME",  # Incubation time
        "DOSE",  # Dose
        "VOLUME",  # Volume
        "WAVELENGTH",  # Wavelength
        "PERCENT",  # Percentage
        "PRESSURE",  # Pressure
        "HUMIDITY",  # Humidity
        "CELL_COUNT",  # Cell count
        "CELL_DENSITY",  # Cell density
        "SERUM",  # Serum percentage
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
