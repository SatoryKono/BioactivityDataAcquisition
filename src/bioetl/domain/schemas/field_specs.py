"""Domain field specifications for schema definitions.

This module provides technology-agnostic field definitions that describe
the structure and constraints of data fields without coupling to any
specific validation framework (e.g., Pandera, Pydantic).

The FieldSpec dataclass captures:
- Field name and data type
- Nullability and description
- Validation constraints (patterns, ranges, allowed values)

These specifications can be transformed into framework-specific schemas
by adapters in the infrastructure layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    # Core types
    "FieldSpec",
    "ConstraintType",
    # Regex patterns (domain knowledge)
    "CHEMBL_ID_PATTERN",
    "BAO_ID_PATTERN",
    "DOI_PATTERN",
    "PUBMED_ID_PATTERN",
    "UNIPROT_ID_PATTERN",
    "HEX_64_PATTERN",
    # Field specifications
    "GENERATED_FIELD_SPECS",
    "ACTIVITY_FIELD_SPECS",
    "ASSAY_FIELD_SPECS",
    "CELL_FIELD_SPECS",
    "MOLECULE_FIELD_SPECS",
    "PUBLICATION_FIELD_SPECS",
    "TARGET_FIELD_SPECS",
    "TISSUE_FIELD_SPECS",
]

# ---------------------------------------------------------------------------
# Domain Regex Patterns (business rules, not framework-specific)
# ---------------------------------------------------------------------------

CHEMBL_ID_PATTERN = r"^CHEMBL\d+$"
BAO_ID_PATTERN = r"^BAO_\d+$"
DOI_PATTERN = r"^10\.\d{4,9}/\S+$"
PUBMED_ID_PATTERN = r"^\d{1,10}$"
HEX_64_PATTERN = r"^[a-f0-9]{64}$"

# UniProt patterns
_UNIPROT_PATTERN_SHORT = r"[A-NR-Z][0-9][A-Z][A-Z0-9]{2}[0-9]"
_UNIPROT_PATTERN_PQ = r"[OPQ][0-9][A-Z0-9]{3}[0-9]"
_UNIPROT_PATTERN_LONG = r"[A-NR-Z][0-9][A-Z][A-Z0-9]{2}[0-9][A-Z0-9]{3}[0-9]"
UNIPROT_ID_PATTERN = (
    f"^(?:{_UNIPROT_PATTERN_PQ}|{_UNIPROT_PATTERN_SHORT}|{_UNIPROT_PATTERN_LONG})$"
)

# ---------------------------------------------------------------------------
# Constraint Types
# ---------------------------------------------------------------------------

# Type alias for constraint dictionaries
ConstraintType = dict[str, Any]


def _range_constraint(
    *,
    ge: float | int | None = None,
    le: float | int | None = None,
    gt: float | int | None = None,
    lt: float | int | None = None,
) -> ConstraintType:
    """Create a range constraint specification."""
    result: ConstraintType = {}
    if ge is not None:
        result["ge"] = ge
    if le is not None:
        result["le"] = le
    if gt is not None:
        result["gt"] = gt
    if lt is not None:
        result["lt"] = lt
    return result


def _enum_constraint(values: list[str]) -> ConstraintType:
    """Create an enumeration constraint specification."""
    return {"isin": values}


# ---------------------------------------------------------------------------
# FieldSpec Dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """Technology-agnostic field specification.

    Attributes
    ----------
    name
        Field/column name.
    data_type
        Abstract data type: "string", "integer", "number", "boolean",
        "array", "object", or "datetime".
    nullable
        Whether the field can contain null/missing values.
    description
        Human-readable description of the field's purpose.
    pattern
        Optional regex pattern for string validation.
    constraints
        Additional validation constraints:
        - "ge", "le", "gt", "lt": numeric range bounds
        - "isin": list of allowed values (enum)

    Examples
    --------
    >>> FieldSpec("activity_id", "integer", nullable=False, description="Primary key")
    >>> FieldSpec("pchembl_value", "number", constraints={"ge": 0, "le": 15})
    >>> FieldSpec("chembl_id", "string", pattern=CHEMBL_ID_PATTERN)
    """

    name: str
    data_type: str
    nullable: bool = True
    description: str = ""
    pattern: str | None = None
    constraints: ConstraintType = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate field specification."""
        valid_types = {
            "string",
            "integer",
            "number",
            "boolean",
            "array",
            "object",
            "datetime",
        }
        if self.data_type not in valid_types:
            msg = f"Invalid data_type '{self.data_type}'. Must be one of: {valid_types}"
            raise ValueError(msg)


# ---------------------------------------------------------------------------
# Generated (Service) Fields - Common to all schemas
#
# Terminology mapping (column name → canonical term → contract method):
#   hash_row         → record_hash        → compute_fingerprint()
#   hash_business_key → business_key_hash → compute_entity_key()
# ---------------------------------------------------------------------------

GENERATED_FIELD_SPECS: tuple[FieldSpec, ...] = (
    # Canonical term: record_hash (contract method: compute_fingerprint)
    FieldSpec(
        name="hash_row",
        data_type="string",
        nullable=False,
        pattern=HEX_64_PATTERN,
        description="SHA-256 hash of entire row (canonical: record_hash)",
    ),
    # Canonical term: business_key_hash (contract method: compute_entity_key)
    FieldSpec(
        name="hash_business_key",
        data_type="string",
        nullable=True,
        pattern=HEX_64_PATTERN,
        description="SHA-256 hash of business key (canonical: business_key_hash)",
    ),
    FieldSpec(
        name="index",
        data_type="integer",
        nullable=False,
        constraints={"ge": 0},
        description="Row order number",
    ),
    FieldSpec(
        name="database_version",
        data_type="string",
        nullable=True,
        description="Source database version",
    ),
    FieldSpec(
        name="acquisition_timestamp",
        data_type="string",
        nullable=True,
        description="Timestamp when data was acquired from source",
    ),
)

GENERATED_COLUMN_NAMES: tuple[str, ...] = tuple(f.name for f in GENERATED_FIELD_SPECS)


# ---------------------------------------------------------------------------
# Activity Field Specifications
# ---------------------------------------------------------------------------

ACTIVITY_FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec("action_type", "string", description="Action type (agonist, antagonist)"),
    FieldSpec(
        "activity_comment", "string", description="Comment on activity measurement"
    ),
    FieldSpec(
        "activity_id",
        "integer",
        nullable=False,
        constraints={"ge": 1},
        description="Internal activity ID",
    ),
    FieldSpec(
        "activity_properties",
        "string",
        description="Additional activity properties (JSON)",
    ),
    FieldSpec(
        "assay_chembl_id",
        "string",
        nullable=False,
        pattern=CHEMBL_ID_PATTERN,
        description="ChEMBL assay identifier",
    ),
    FieldSpec("assay_description", "string", description="Textual assay description"),
    FieldSpec(
        "assay_type",
        "string",
        nullable=False,
        constraints={"isin": ["B", "F", "b", "f"]},
        description="Assay type (B=binding, F=functional)",
    ),
    FieldSpec(
        "assay_variant_accession", "string", description="Protein variant accession"
    ),
    FieldSpec(
        "assay_variant_mutation",
        "string",
        description="Protein variant mutation description",
    ),
    FieldSpec(
        "bao_endpoint",
        "string",
        pattern=BAO_ID_PATTERN,
        description="BioAssay Ontology endpoint term",
    ),
    FieldSpec(
        "bao_format",
        "string",
        pattern=BAO_ID_PATTERN,
        description="BioAssay Ontology format term",
    ),
    FieldSpec("bao_label", "string", description="BAO endpoint/format label"),
    FieldSpec("canonical_smiles", "string", description="Canonical SMILES of molecule"),
    FieldSpec(
        "data_validity_comment", "string", description="Data quality/validity comment"
    ),
    FieldSpec(
        "data_validity_description", "string", description="Description of data issues"
    ),
    FieldSpec(
        "document_chembl_id",
        "string",
        nullable=False,
        pattern=CHEMBL_ID_PATTERN,
        description="ChEMBL document identifier",
    ),
    FieldSpec("document_journal", "string", description="Journal name"),
    FieldSpec("document_year", "number", description="Publication year"),
    FieldSpec(
        "ligand_efficiency", "string", description="Ligand efficiency metrics (JSON)"
    ),
    FieldSpec(
        "molecule_chembl_id",
        "string",
        nullable=False,
        pattern=CHEMBL_ID_PATTERN,
        description="ChEMBL molecule identifier",
    ),
    FieldSpec("molecule_pref_name", "string", description="Molecule preferred name"),
    FieldSpec(
        "parent_molecule_chembl_id",
        "string",
        pattern=CHEMBL_ID_PATTERN,
        description="Parent molecule ChEMBL ID",
    ),
    FieldSpec(
        "pchembl_value",
        "number",
        constraints={"ge": 0, "le": 15},
        description="Normalized activity (-log10, range 0-15)",
    ),
    FieldSpec(
        "potential_duplicate", "boolean", description="Flag for potential duplicate"
    ),
    FieldSpec("qudt_units", "string", description="QUDT units URI"),
    FieldSpec(
        "record_id",
        "number",
        constraints={"ge": 1},
        description="Compound record ID",
    ),
    FieldSpec(
        "relation",
        "string",
        constraints={"isin": ["="]},
        description="Original relation (=)",
    ),
    FieldSpec("src_id", "number", description="Data source ID"),
    FieldSpec(
        "standard_flag",
        "boolean",
        nullable=False,
        description="Flag indicating standardized type/value",
    ),
    FieldSpec(
        "standard_relation",
        "string",
        constraints={"isin": ["="]},
        description="Standardized relation",
    ),
    FieldSpec(
        "standard_text_value",
        "string",
        description="Standardized text for qualitative values",
    ),
    FieldSpec("standard_type", "string", description="Standardized activity type"),
    FieldSpec("standard_units", "string", description="Standardized units"),
    FieldSpec(
        "standard_upper_value",
        "number",
        description="Upper bound of standardized interval",
    ),
    FieldSpec("standard_value", "number", description="Standardized numeric value"),
    FieldSpec(
        "target_chembl_id",
        "string",
        pattern=CHEMBL_ID_PATTERN,
        description="ChEMBL target identifier",
    ),
    FieldSpec("target_organism", "string", description="Target organism"),
    FieldSpec("target_pref_name", "string", description="Target preferred name"),
    FieldSpec("target_tax_id", "number", description="Target NCBI Taxonomy ID"),
    FieldSpec("text_value", "string", description="Original text value"),
    FieldSpec("toid", "string", description="Target Ontology ID"),
    FieldSpec("type", "string", description="Original activity type"),
    FieldSpec("units", "string", description="Original measurement units"),
    FieldSpec("uo_units", "string", description="Unit Ontology ID"),
    FieldSpec("upper_value", "number", description="Upper bound of original interval"),
    FieldSpec("value", "number", description="Original numeric value"),
)


# ---------------------------------------------------------------------------
# Assay Field Specifications
# ---------------------------------------------------------------------------

ASSAY_FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec("aidx", "string", description="Internal assay index/depositor ID"),
    FieldSpec(
        "assay_category",
        "string",
        description="Assay category (primary/confirmatory/screening)",
    ),
    FieldSpec("assay_cell_type", "string", description="Cell line type if applicable"),
    FieldSpec(
        "assay_chembl_id",
        "string",
        nullable=False,
        pattern=CHEMBL_ID_PATTERN,
        description="ChEMBL assay identifier",
    ),
    FieldSpec(
        "assay_classifications",
        "string",
        description="Assay classifications (BAO, etc.)",
    ),
    FieldSpec("assay_group", "string", description="Assay group/series"),
    FieldSpec("assay_organism", "string", description="Testing system organism"),
    FieldSpec("assay_parameters", "string", description="Assay parameters (JSON)"),
    FieldSpec("assay_strain", "string", description="Organism strain"),
    FieldSpec(
        "assay_subcellular_fraction", "string", description="Subcellular fraction"
    ),
    FieldSpec("assay_tax_id", "number", description="NCBI Taxonomy ID"),
    FieldSpec(
        "assay_test_type",
        "string",
        description="Test type (in vitro, in vivo, ex vivo)",
    ),
    FieldSpec("assay_tissue", "string", description="Tissue used in assay"),
    FieldSpec(
        "assay_type",
        "string",
        nullable=False,
        constraints={"isin": ["B", "F", "A", "T", "P", "U"]},
        description="Assay type (B=binding, F=functional, A=ADMET, T=toxicity, P=physicochemical, U=unknown)",
    ),
    FieldSpec("assay_type_description", "string", description="Assay type description"),
    FieldSpec(
        "bao_format",
        "string",
        pattern=BAO_ID_PATTERN,
        description="BioAssay Ontology format",
    ),
    FieldSpec("bao_label", "string", description="BAO format label"),
    FieldSpec(
        "cell_chembl_id",
        "string",
        pattern=CHEMBL_ID_PATTERN,
        description="ChEMBL cell line identifier",
    ),
    FieldSpec(
        "confidence_description", "string", description="Confidence level description"
    ),
    FieldSpec(
        "confidence_score",
        "integer",
        constraints={"ge": 0, "le": 9},
        description="Target mapping confidence (0-9)",
    ),
    FieldSpec("description", "string", description="Assay description"),
    FieldSpec(
        "document_chembl_id",
        "string",
        pattern=CHEMBL_ID_PATTERN,
        description="ChEMBL document identifier",
    ),
    FieldSpec(
        "relationship_description",
        "string",
        description="Relationship type description",
    ),
    FieldSpec(
        "relationship_type",
        "string",
        constraints={
            "isin": [
                "D",
                "H",
                "M",
                "N",
                "P",
                "T",
                "U",
                "d",
                "h",
                "m",
                "n",
                "p",
                "t",
                "u",
            ]
        },
        description="Assay-target relationship type",
    ),
    FieldSpec("score", "number", description="Search ranking score"),
    FieldSpec("src_assay_id", "string", description="Source database assay ID"),
    FieldSpec("src_id", "number", description="Data source ID"),
    FieldSpec(
        "target_chembl_id",
        "string",
        pattern=CHEMBL_ID_PATTERN,
        description="ChEMBL target identifier",
    ),
    FieldSpec(
        "tissue_chembl_id",
        "string",
        pattern=CHEMBL_ID_PATTERN,
        description="ChEMBL tissue identifier",
    ),
    FieldSpec(
        "variant_sequence",
        "string",
        description="Protein variant sequence if target is protein",
    ),
)


# ---------------------------------------------------------------------------
# Cell Field Specifications
# ---------------------------------------------------------------------------

CELL_FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec(
        "cell_chembl_id",
        "string",
        nullable=False,
        pattern=CHEMBL_ID_PATTERN,
        description="Primary ChEMBL cell identifier",
    ),
    FieldSpec("cell_name", "string", description="Preferred cell line name"),
    FieldSpec(
        "cell_source_organism",
        "string",
        description="Organism the cell line originates from",
    ),
    FieldSpec(
        "cell_type",
        "string",
        description="High-level cell type (epithelial, stem, etc.)",
    ),
    FieldSpec(
        "cell_description", "string", description="Free text cell line description"
    ),
)


# ---------------------------------------------------------------------------
# Molecule Field Specifications
# ---------------------------------------------------------------------------

MOLECULE_FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec(
        "atc_classifications", "string", description="ATC codes and descriptions"
    ),
    FieldSpec("availability_type", "number", description="Availability type (0/1/2)"),
    FieldSpec("black_box_warning", "number", description="Black box warning flag"),
    FieldSpec("chemical_probe", "number", description="Chemical probe flag"),
    FieldSpec("chirality", "number", description="Chirality code"),
    FieldSpec("cross_references", "string", description="External cross-references"),
    FieldSpec("dosed_ingredient", "boolean", description="Used as dosed ingredient"),
    FieldSpec("first_approval", "number", description="Year of first approval"),
    FieldSpec("first_in_class", "number", description="First in class flag"),
    FieldSpec("helm_notation", "string", description="HELM notation"),
    FieldSpec("inorganic_flag", "number", description="Inorganic compound flag"),
    FieldSpec(
        "max_phase",
        "number",
        constraints={"ge": 0, "le": 4},
        description="Maximum clinical trial phase",
    ),
    FieldSpec(
        "molecule_chembl_id",
        "string",
        nullable=False,
        pattern=CHEMBL_ID_PATTERN,
        description="ChEMBL molecule identifier",
    ),
    FieldSpec("molecule_hierarchy", "string", description="Molecule hierarchy (JSON)"),
    FieldSpec(
        "molecule_properties", "string", description="Physicochemical properties (JSON)"
    ),
    FieldSpec(
        "molecule_structures", "string", description="Structural representations (JSON)"
    ),
    FieldSpec("molecule_synonyms", "string", description="Molecule synonyms (JSON)"),
    FieldSpec(
        "molecule_type",
        "string",
        description="Molecule type (Small molecule, Protein, etc.)",
    ),
    FieldSpec("natural_product", "number", description="Natural product flag"),
    FieldSpec("oral", "boolean", description="Oral administration"),
    FieldSpec("orphan", "number", description="Orphan drug status"),
    FieldSpec("parenteral", "boolean", description="Parenteral administration"),
    FieldSpec("polymer_flag", "number", description="Polymer flag"),
    FieldSpec("pref_name", "string", description="Preferred molecule name"),
    FieldSpec("prodrug", "number", description="Prodrug flag"),
    FieldSpec("structure_type", "string", description="Structure representation type"),
    FieldSpec("therapeutic_flag", "boolean", description="Therapeutic agent flag"),
    FieldSpec("topical", "boolean", description="Topical administration"),
    FieldSpec("usan_stem", "string", description="USAN stem"),
    FieldSpec("usan_stem_definition", "string", description="USAN stem definition"),
    FieldSpec("usan_substem", "string", description="USAN substem"),
    FieldSpec("usan_year", "number", description="USAN assignment year"),
    FieldSpec("veterinary", "number", description="Veterinary use flag"),
    FieldSpec("withdrawn_flag", "boolean", description="Withdrawn from market flag"),
)


# ---------------------------------------------------------------------------
# Publication Field Specifications
# ---------------------------------------------------------------------------

PUBLICATION_FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec("abstract", "string", description="Document abstract"),
    FieldSpec("authors", "string", description="List of authors"),
    FieldSpec(
        "chembl_release", "string", description="ChEMBL release when document appeared"
    ),
    FieldSpec("contact", "string", description="Contact for deposited datasets"),
    FieldSpec(
        "doc_type",
        "string",
        nullable=False,
        constraints={"isin": ["PUBLICATION", "DATASET", "PATENT", "OTHER"]},
        description="Document type",
    ),
    FieldSpec(
        "document_chembl_id",
        "string",
        nullable=False,
        pattern=CHEMBL_ID_PATTERN,
        description="ChEMBL document identifier",
    ),
    FieldSpec("doi", "string", pattern=DOI_PATTERN, description="DOI (normalized)"),
    FieldSpec("doi_chembl", "string", description="Internal ChEMBL DOI for datasets"),
    FieldSpec("first_page", "string", description="First page number"),
    FieldSpec("issue", "string", description="Journal issue number"),
    FieldSpec("journal", "string", description="Abbreviated journal name"),
    FieldSpec("journal_full_title", "string", description="Full journal title"),
    FieldSpec("last_page", "string", description="Last page number"),
    FieldSpec("patent_id", "string", description="Patent identifier"),
    FieldSpec(
        "pubmed_id", "string", pattern=PUBMED_ID_PATTERN, description="PubMed ID"
    ),
    FieldSpec("score", "number", description="Search ranking score"),
    FieldSpec("src_id", "number", description="Data source ID"),
    FieldSpec("title", "string", description="Document title"),
    FieldSpec("volume", "string", description="Journal volume"),
    FieldSpec("year", "number", description="Publication year"),
)


# ---------------------------------------------------------------------------
# Target Field Specifications
# ---------------------------------------------------------------------------

TARGET_FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec(
        "target_chembl_id",
        "string",
        nullable=False,
        pattern=CHEMBL_ID_PATTERN,
        description="ChEMBL target identifier",
    ),
    FieldSpec("pref_name", "string", description="Target preferred name"),
    FieldSpec("score", "number", description="Search ranking score"),
    FieldSpec("organism", "string", description="Target organism"),
    FieldSpec(
        "target_type",
        "string",
        nullable=False,
        description="Target type (SINGLE PROTEIN, FAMILY, etc.)",
    ),
    FieldSpec("tax_id", "number", description="NCBI Taxonomy ID"),
    FieldSpec("species_group_flag", "boolean", description="Species group target flag"),
    FieldSpec("target_components", "string", description="Target components (JSON)"),
    FieldSpec("cross_references", "string", description="External cross-references"),
    FieldSpec(
        "uniprot_id",
        "string",
        pattern=UNIPROT_ID_PATTERN,
        description="Primary UniProt ID",
    ),
)


# ---------------------------------------------------------------------------
# Tissue Field Specifications
# ---------------------------------------------------------------------------

TISSUE_FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec(
        "tissue_chembl_id",
        "string",
        nullable=False,
        pattern=CHEMBL_ID_PATTERN,
        description="Primary ChEMBL tissue identifier",
    ),
    FieldSpec("tissue_name", "string", description="Preferred tissue name"),
    FieldSpec(
        "tissue_source_organism",
        "string",
        description="Organism the tissue sample originates from",
    ),
    FieldSpec(
        "tissue_description", "string", description="Free text tissue description"
    ),
    FieldSpec(
        "tissue_type", "string", description="High-level tissue type or classification"
    ),
)
