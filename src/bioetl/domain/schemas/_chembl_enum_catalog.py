"""Single immutable Python catalog for ChEMBL enum-like value sets.

This module is the reviewed code-side SSOT consumed by both domain schema
constants and profile vocabulary lookup. Config-backed YAML registries remain
the published external surface and are kept in parity by config tests.
"""

from __future__ import annotations

from bioetl.domain.schemas._chembl_enum_catalog_target_publication import (
    OA_STATUS_VALUES,
    PUBLICATION_TERM_TYPES,
    PUBLICATION_TYPES,
    TARGET_COMPONENT_RELATIONSHIPS,
    TARGET_COMPONENT_TYPES,
    TARGET_ORGANISM_CLASSES,
    TARGET_TYPES,
)

STANDARD_RELATIONS: frozenset[str] = frozenset(["=", "<", "<=", ">", ">=", "~"])

ACTIVITY_ACTION_TYPES: frozenset[str] = frozenset(
    [
        "AGONIST",
        "ANTAGONIST",
        "INHIBITOR",
        "PARTIAL AGONIST",
    ]
)

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

ASSAY_PARAMETER_STANDARD_TYPES: frozenset[str] = frozenset(
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
        "CONC",
        "PH",
        "TEMP",
        "TIME",
        "DOSE",
        "VOLUME",
        "WAVELENGTH",
        "PERCENT",
        "PRESSURE",
        "HUMIDITY",
        "CELL_COUNT",
        "CELL_DENSITY",
        "SERUM",
    ]
)

BINARY_FLAG_VALUES: frozenset[str] = frozenset(["0", "1"])
TRINARY_FLAG_VALUES: frozenset[str] = frozenset(["-1", "0", "1"])

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

ASSAY_TYPES: frozenset[str] = frozenset(["B", "F", "A", "T", "P", "U"])
ONTOLOGY_MAPPING_STATUSES: frozenset[str] = frozenset(["mapped", "unmapped", "missing"])
ASSAY_TEST_TYPES: frozenset[str] = frozenset(["In vivo", "In vitro", "Ex vivo"])
ASSAY_CATEGORIES: frozenset[str] = frozenset(
    [
        "screening",
        "confirmatory",
        "panel",
        "summary",
        "other",
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
ASSAY_GROUPS: frozenset[str] = frozenset(["FUNCTIONAL", "BINDING"])
SUBCELLULAR_FRACTIONS: frozenset[str] = frozenset(
    [
        "Membrane",
        "Nucleus",
        "Cytoplasm",
        "Mitochondria",
        "Microsomes",
        "Endoplasmic reticulum",
    ]
)
CONFIDENCE_DESCRIPTIONS: frozenset[str] = frozenset(
    [
        "Default value - Target unknown or has yet to be assigned",
        "Direct protein complex subunits assigned",
        "Direct single protein target assigned",
        "Homologous single protein target assigned",
        "Multiple direct protein targets may be assigned",
        "Multiple homologous protein targets may be assigned",
        "Target assigned is molecular non-protein target",
        "Target assigned is non-molecular",
    ]
)
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
RO3_PASS_VALUES: frozenset[str] = frozenset(["Y", "N"])
MAX_PHASE_VALUES: tuple[float, ...] = (-1, 0, 0.5, 1, 2, 3, 4)
CHIRALITY_VALUES: tuple[int, ...] = (-1, 0, 1, 2)
AVAILABILITY_TYPE_VALUES: tuple[int, ...] = (-2, -1, 0, 1, 2)

_MAPPING_STATUS_FIELDS: tuple[tuple[str, str], ...] = (
    ("activity", "bao_endpoint_mapping_status"),
    ("activity", "bao_format_mapping_status"),
    ("activity", "qudt_unit_mapping_status"),
    ("activity", "uo_unit_mapping_status"),
    ("assay", "bao_format_mapping_status"),
    ("assay_parameters", "qudt_unit_mapping_status"),
    ("assay_parameters", "uo_unit_mapping_status"),
    ("cell_line", "clo_mapping_status"),
    ("cell_line", "efo_mapping_status"),
    ("tissue", "bto_mapping_status"),
    ("tissue", "efo_mapping_status"),
    ("tissue", "uberon_mapping_status"),
)

CHEMBL_ENUM_CATALOG: dict[tuple[str, str], frozenset[str]] = {
    ("activity", "action_type"): ACTIVITY_ACTION_TYPES,
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
    ("assay", "assay_subcellular_fraction"): SUBCELLULAR_FRACTIONS,
    ("assay", "subcellular_fraction"): SUBCELLULAR_FRACTIONS,
    ("assay", "subcellular_fractions"): SUBCELLULAR_FRACTIONS,
    ("assay_parameters", "parameter_type"): ASSAY_PARAMETER_STANDARD_TYPES,
    ("assay_parameters", "type"): ASSAY_PARAMETER_STANDARD_TYPES,
    ("assay_parameters", "standard_relation"): STANDARD_RELATIONS,
    ("assay_parameters", "standard_type"): ASSAY_PARAMETER_STANDARD_TYPES,
    ("assay_parameters", "standard_units"): ACTIVITY_STANDARD_UNITS,
    ("molecule", "availability_type"): frozenset(
        str(value) for value in AVAILABILITY_TYPE_VALUES
    ),
    ("molecule", "black_box_warning"): BINARY_FLAG_VALUES,
    ("molecule", "chirality"): frozenset(str(value) for value in CHIRALITY_VALUES),
    ("molecule", "dosed_ingredient"): BINARY_FLAG_VALUES,
    ("molecule", "first_in_class"): TRINARY_FLAG_VALUES,
    ("molecule", "inorganic_flag"): TRINARY_FLAG_VALUES,
    ("molecule", "max_phase"): frozenset(str(value) for value in MAX_PHASE_VALUES),
    ("molecule", "molecule_type"): MOLECULE_TYPES,
    ("molecule", "natural_product"): TRINARY_FLAG_VALUES,
    ("molecule", "polymer_flag"): BINARY_FLAG_VALUES,
    ("molecule", "prodrug"): TRINARY_FLAG_VALUES,
    ("molecule", "ro3_pass"): RO3_PASS_VALUES,
    ("molecule", "structure_type"): STRUCTURE_TYPES,
    ("publication", "oa_status"): frozenset(OA_STATUS_VALUES),
    ("publication", "publication_type"): frozenset(
        ["journal-article", "book", "dataset", "patent"]
    ),  # ChEMBL-specific subset
    ("publication_term", "term_type"): PUBLICATION_TERM_TYPES,
    ("target", "component_relationships"): TARGET_COMPONENT_RELATIONSHIPS,
    ("target", "component_types"): TARGET_COMPONENT_TYPES,
    ("target", "organism_class"): TARGET_ORGANISM_CLASSES,
    ("target", "target_type"): TARGET_TYPES,
    ("subcellular_fraction", "subcellular_fraction"): SUBCELLULAR_FRACTIONS,
    ("target_component", "component_type"): TARGET_COMPONENT_TYPES,
    **dict.fromkeys(_MAPPING_STATUS_FIELDS, ONTOLOGY_MAPPING_STATUSES),
}

__all__ = [
    "ACTIVITY_ACTION_TYPES",
    "ACTIVITY_STANDARD_TYPES",
    "ACTIVITY_STANDARD_UNITS",
    "ASSAY_CATEGORIES",
    "ASSAY_GROUPS",
    "ASSAY_PARAMETER_STANDARD_TYPES",
    "ASSAY_TEST_TYPES",
    "ASSAY_TYPES",
    "AVAILABILITY_TYPE_VALUES",
    "BINARY_FLAG_VALUES",
    "CHEMBL_ENUM_CATALOG",
    "CHIRALITY_VALUES",
    "CONFIDENCE_DESCRIPTIONS",
    "DATA_VALIDITY_COMMENTS",
    "MAX_PHASE_VALUES",
    "MOLECULE_TYPES",
    "OA_STATUS_VALUES",
    "ONTOLOGY_MAPPING_STATUSES",
    "PUBLICATION_TERM_TYPES",
    "PUBLICATION_TYPES",
    "RELATIONSHIP_TYPES",
    "RO3_PASS_VALUES",
    "STANDARD_RELATIONS",
    "STRUCTURE_TYPES",
    "SUBCELLULAR_FRACTIONS",
    "TARGET_COMPONENT_RELATIONSHIPS",
    "TARGET_COMPONENT_TYPES",
    "TARGET_ORGANISM_CLASSES",
    "TARGET_TYPES",
    "TRINARY_FLAG_VALUES",
]
