"""Centralized immutable constants for schema validation.

Enum values originate from `configs/enums/chembl.yaml` and are kept in sync by
`tests/unit/domain/schemas/test_constants_yaml.py`.
"""

from __future__ import annotations

from bioetl.domain.schemas._schema_validation_patterns import (
    BAO_ID_PATTERN,
    BTO_ID_PATTERN,
    CALOHA_ID_PATTERN,
    CELLOSAURUS_ID_PATTERN,
    CHEMBL_ID_PATTERN,
    CLO_ID_PATTERN,
    EFO_ID_PATTERN,
    ISO_DATE_PATTERN,
    ISSN_PATTERN,
    ORCID_PATTERN,
    UBERON_ID_PATTERN,
    UO_ID_PATTERN,
)

# =============================================================================
# CHEMBL ACTIVITY ENUMS
# =============================================================================

STANDARD_RELATIONS: frozenset[str] = frozenset(["=", "<", "<=", ">", ">=", "~"])

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

ACTIVITY_STANDARD_UNITS: frozenset[str] = frozenset(
    [
        "nM",
        "µM",
        "mM",
        "pM",
        "M",
        "%",
        "ug.mL-1",
        "mg.kg-1",
    ]
)

# =============================================================================
# CHEMBL ASSAY ENUMS
# =============================================================================

ASSAY_TYPES: frozenset[str] = frozenset(["B", "F", "A", "T", "P", "U"])

ASSAY_TEST_TYPES: frozenset[str] = frozenset(["In vivo", "In vitro", "Ex vivo"])

ASSAY_CATEGORIES: frozenset[str] = frozenset(
    [
        # Classic categories
        "screening",
        "confirmatory",
        "panel",
        "summary",
        "other",
        # Extended categories (ChEMBL 35+)
        "Affinity biochemical assay",
        "Affinity on-target cellular assay",
        "Affinity phenotypic cellular assay",
        "Alphascreen assay",
        "Cell health data",
        "GPCR beta-arrestin recruitment assay",
        "HTRF assay",
        "ITC assay",
        "Incucyte cell viability",
        "NanoBRET assay",
        "PDSP assay",
        "Selectivity assay",
        "Thermal shift assay",
    ]
)

RELATIONSHIP_TYPES: frozenset[str] = frozenset(["D", "H", "M", "N", "S", "U"])

# Additional assay enums
ASSAY_GROUPS: frozenset[str] = frozenset(["FUNCTIONAL", "BINDING"])
SUBCELLULAR_FRACTIONS: frozenset[str] = frozenset(
    ["Membrane", "Nucleus", "Cytoplasm", "Mitochondria", "Endoplasmic reticulum"]
)
CONFIDENCE_DESCRIPTIONS: frozenset[str] = frozenset(
    [
        "Likely active",
        "Active",
        "Inactive",
        "Potentially active",
        "Potentially inactive",
        "Inconclusive",
        "Not determined",
    ]
)

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
        # Canonical kebab-case values after normalization by
        # normalize_publication_type() (see domain.mapping.publication_type_mapping).
        "journal-article",
        "patent",
        "dataset",
        "book",
        "review",
        "letter",
        "editorial",
        "clinical-trial",
        "meta-analysis",
        "case-reports",
        "comparative-study",
        "evaluation-study",
        "preprint",
        "book-chapter",
        "proceedings-article",
        "posted-content",
        "report",
        "standard",
        "dissertation",
        "other",
    ]
)

PUBLICATION_TERM_TYPES: frozenset[str] = frozenset(
    [
        "MESH_HEADING",
        "MESH_QUALIFIER",
        "KEYWORD",
        "CONCEPT",
    ]
)

# =============================================================================
# CANONICAL VALIDATION BOUNDS (Gold / Composite layer)
# =============================================================================
# Unified bounds for fields shared across providers (ChEMBL, PubChem).
# Silver schemas retain provider-specific bounds; these apply to Gold output.
# RF-NORM-02: Normalization Unification Plan.

CANONICAL_MOLECULAR_WEIGHT_RANGE: tuple[float, float] = (0.0, 100_000.0)
CANONICAL_HBA_COUNT_RANGE: tuple[int, int] = (0, 200)
CANONICAL_HBD_COUNT_RANGE: tuple[int, int] = (0, 200)
CANONICAL_ROTATABLE_BOND_COUNT_RANGE: tuple[int, int] = (0, 500)
CANONICAL_HEAVY_ATOM_COUNT_RANGE: tuple[int, int] = (0, 2000)
CANONICAL_LOGP_RANGE: tuple[float, float] = (-30.0, 30.0)
CANONICAL_POLAR_SURFACE_AREA_RANGE: tuple[float, float] = (0.0, 5000.0)
CANONICAL_SMILES_MAX_LENGTH: int = 20_000

# =============================================================================
# EXPORTS (for explicit re-export in __init__.py)
# =============================================================================

__all__ = [
    "ACTIVITY_STANDARD_TYPES",
    "ASSAY_CATEGORIES",
    # Assay enums
    "ASSAY_CATEGORIES",
    "ASSAY_GROUPS",
    "ASSAY_PARAMETER_STANDARD_TYPES",
    "ASSAY_TEST_TYPES",
    "ASSAY_TEST_TYPES",
    "ASSAY_TYPES",
    "BAO_ID_PATTERN",
    # Regex patterns
    "BTO_ID_PATTERN",
    "CALOHA_ID_PATTERN",
    # Canonical validation bounds (Gold / Composite)
    "CANONICAL_HBA_COUNT_RANGE",
    "CANONICAL_HBD_COUNT_RANGE",
    "CANONICAL_HEAVY_ATOM_COUNT_RANGE",
    "CANONICAL_LOGP_RANGE",
    "CANONICAL_MOLECULAR_WEIGHT_RANGE",
    "CANONICAL_POLAR_SURFACE_AREA_RANGE",
    "CANONICAL_ROTATABLE_BOND_COUNT_RANGE",
    "CANONICAL_SMILES_MAX_LENGTH",
    "CELLOSAURUS_ID_PATTERN",
    "CHEMBL_ID_PATTERN",
    "CLO_ID_PATTERN",
    "CONFIDENCE_DESCRIPTIONS",
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
    "RELATIONSHIP_TYPES",
    # Activity enums
    "STANDARD_RELATIONS",
    "STRUCTURE_TYPES",
    "SUBCELLULAR_FRACTIONS",
    "TARGET_COMPONENT_RELATIONSHIPS",
    # Target enums
    "TARGET_TYPES",
    "UBERON_ID_PATTERN",
    "UO_ID_PATTERN",
]
