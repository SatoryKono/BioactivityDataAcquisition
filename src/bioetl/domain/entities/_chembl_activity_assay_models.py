# mypy: disable-error-code="misc"
"""ChEMBL activity/assay DTO models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ActivityRecord(BaseModel):
    """Bioactivity measurement DTO from ChEMBL.

    Represents a single activity measurement from ChEMBL API.
    Required fields: activity_id, molecule_id.

    Example:
        >>> record = ActivityRecord(
        ...     activity_id="12345",
        ...     molecule_id="CHEMBL25",
        ...     assay_id="CHEMBL1000",
        ...     standard_type="IC50",
        ...     standard_value=5.0,
        ...     standard_units="nM",
        ... )
        >>> record.model_dump()
        {'activity_id': '12345', 'molecule_id': 'CHEMBL25', ...}
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    activity_id: str = Field(description="Unique activity identifier")

    # Core identifiers (REQUIRED: molecule_id)
    molecule_id: str = Field(description="ChEMBL ID of tested molecule")
    assay_id: str | None = Field(default=None, description="ChEMBL ID of the assay")
    target_id: str | None = Field(default=None, description="ChEMBL ID of the target")
    publication_id: str | None = Field(
        default=None, description="ChEMBL ID of the source document"
    )

    # Standardized activity values
    standard_type: str | None = Field(
        default=None, description="Standardized measurement type (IC50, EC50, Ki, etc.)"
    )
    standard_value: float | None = Field(
        default=None, description="Standardized activity value"
    )
    standard_units: str | None = Field(
        default=None, description="Standardized units (nM, uM, etc.)"
    )
    standard_relation: str | None = Field(
        default=None, description="Relation operator (=, <, >, etc.)"
    )
    standard_upper_value: float | None = Field(
        default=None, description="Standardized upper bound for ranges"
    )
    standard_text_value: str | None = Field(
        default=None, description="Standardized text value"
    )
    standard_flag: int | None = Field(
        default=None, description="Standardization flag (0 or 1)"
    )

    # Derived metrics
    pchembl_value: float | None = Field(
        default=None, description="-log10 of molar activity value"
    )

    # Original (non-standardized) values
    type: str | None = Field(default=None, description="Original measurement type")
    value: float | None = Field(default=None, description="Original activity value")
    units: str | None = Field(default=None, description="Original units")
    relation: str | None = Field(default=None, description="Original relation operator")
    upper_value: float | None = Field(default=None, description="Original upper bound")
    text_value: str | None = Field(default=None, description="Original text value")

    # Molecule data (denormalized)
    canonical_smiles: str | None = Field(
        default=None, description="Canonical SMILES structure"
    )
    molecule_pref_name: str | None = Field(
        default=None, description="Molecule preferred name"
    )
    parent_molecule_id: str | None = Field(
        default=None, description="Parent molecule ChEMBL ID"
    )

    # Target data (denormalized)
    target_pref_name: str | None = Field(
        default=None, description="Target preferred name"
    )
    target_organism: str | None = Field(
        default=None, description="Target organism name"
    )
    target_tax_id: int | None = Field(default=None, description="Target taxonomy ID")

    # Assay data (denormalized)
    assay_type: str | None = Field(default=None, description="Assay type code (B/F/A)")
    assay_description: str | None = Field(
        default=None, description="Assay description text"
    )
    assay_variant_accession: str | None = Field(
        default=None, description="Variant UniProt accession"
    )
    assay_variant_mutation: str | None = Field(
        default=None, description="Variant mutation description"
    )

    # BioAssay Ontology annotations
    bao_endpoint: str | None = Field(default=None, description="BAO endpoint ID")
    bao_format: str | None = Field(default=None, description="BAO format ID")
    bao_label: str | None = Field(default=None, description="BAO label")

    # Unit ontologies
    qudt_units: str | None = Field(default=None, description="QUDT unit URI")
    uo_units: str | None = Field(default=None, description="Units Ontology ID")

    # Source and record info
    src_id: int | None = Field(default=None, description="Data source ID")
    record_id: int | None = Field(
        default=None, description="FK to compound_record table"
    )
    toid: int | None = Field(default=None, description="Test Occasion ID")

    # Document data (denormalized)
    journal: str | None = Field(default=None, description="Source journal name")
    publication_year: int | None = Field(default=None, description="Publication year")

    # Data quality annotations
    activity_comment: str | None = Field(
        default=None, description="Activity textual comment"
    )
    data_validity_comment: str | None = Field(
        default=None, description="Data quality comment"
    )
    data_validity_description: str | None = Field(
        default=None, description="Data validity description"
    )
    potential_duplicate: int | None = Field(
        default=None, description="Potential duplicate flag"
    )

    # Ligand efficiency metrics (flattened)
    ligand_efficiency_bei: float | None = Field(
        default=None, description="Binding Efficiency Index"
    )
    ligand_efficiency_le: float | None = Field(
        default=None, description="Ligand Efficiency"
    )
    ligand_efficiency_lle: float | None = Field(
        default=None, description="Lipophilic Ligand Efficiency"
    )
    ligand_efficiency_sei: float | None = Field(
        default=None, description="Surface Efficiency Index"
    )

    # Action type (flattened)
    action_type: str | None = Field(
        default=None, description="Action type (INHIBITOR, AGONIST, etc.)"
    )
    action_type_description: str | None = Field(
        default=None, description="Action type description"
    )
    action_type_parent_type: str | None = Field(
        default=None, description="Parent action type"
    )

    # Complex fields (JSON serialized for forensic)
    activity_properties: str | None = Field(
        default=None, description="Activity properties as JSON string"
    )


class AssayRecord(BaseModel):
    """Bioassay definition DTO from ChEMBL.

    Represents a bioassay protocol from ChEMBL API.
    Required field: assay_id.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    assay_id: str = Field(description="Unique assay ChEMBL ID")

    # Core identifiers
    target_id: str | None = Field(default=None, description="Target ChEMBL ID")
    publication_id: str | None = Field(
        default=None, description="Source document ChEMBL ID"
    )
    cell_id: str | None = Field(default=None, description="Cell line ChEMBL ID")
    tissue_id: str | None = Field(default=None, description="Tissue ChEMBL ID")
    src_id: int | None = Field(default=None, description="Data source ID")
    src_assay_id: str | None = Field(
        default=None, description="Original source assay ID"
    )
    aidx: str | None = Field(default=None, description="Assay index")

    # Assay classification
    assay_type: str | None = Field(
        default=None, description="Assay type code (B/F/A/T/P/U)"
    )
    assay_type_description: str | None = Field(
        default=None, description="Full assay type description"
    )
    assay_category: str | None = Field(default=None, description="Assay category")
    assay_test_type: str | None = Field(
        default=None, description="Test type (in vivo/in vitro)"
    )
    assay_group: str | None = Field(default=None, description="Assay group")

    # Biological context
    assay_organism: str | None = Field(
        default=None, description="Organism used in assay"
    )
    assay_tax_id: int | None = Field(
        default=None, description="NCBI Taxonomy ID for assay organism"
    )
    assay_cell_type: str | None = Field(default=None, description="Cell type used")
    assay_tissue: str | None = Field(default=None, description="Tissue type used")
    assay_strain: str | None = Field(default=None, description="Strain used")
    assay_subcellular_fraction: str | None = Field(
        default=None, description="Subcellular fraction"
    )

    # BioAssay Ontology annotations
    bao_format: str | None = Field(default=None, description="BAO format ID")
    bao_label: str | None = Field(default=None, description="BAO label")

    # Description and confidence
    description: str | None = Field(default=None, description="Full assay description")
    confidence_score: int | None = Field(
        default=None, description="Target confidence score (0-9)"
    )
    confidence_description: str | None = Field(
        default=None, description="Confidence level description"
    )
    relationship_type: str | None = Field(
        default=None, description="Target-assay relationship type"
    )
    relationship_description: str | None = Field(
        default=None, description="Relationship description"
    )

    # Additional metadata
    assay_pref_name: str | None = Field(
        default=None, description="Preferred assay name"
    )
    score: float | None = Field(
        default=None, description="Assay score (distinct from confidence)"
    )

    # Variant information (flattened)
    variant_accession: str | None = Field(
        default=None, description="Variant UniProt accession"
    )
    variant_isoform: str | None = Field(default=None, description="Variant isoform")
    variant_mutation: str | None = Field(
        default=None, description="Variant mutation (e.g., V600E)"
    )
    variant_organism: str | None = Field(default=None, description="Variant organism")
    variant_sequence: str | None = Field(
        default=None, description="Variant amino amolecule_id sequence"
    )
    variant_tax_id: int | None = Field(
        default=None, description="Variant NCBI Taxonomy ID"
    )

    # Complex fields (JSON serialized)
    assay_classifications: str | None = Field(
        default=None, description="Assay classifications as JSON"
    )
    assay_parameters: str | None = Field(
        default=None, description="Assay parameters as JSON"
    )
    # NOTE: _json suffix retained — forensic raw dump, not a renamed business field
    variant_sequence_json: str | None = Field(
        default=None, description="Original variant sequence as JSON"
    )


__all__ = [
    "ActivityRecord",
    "AssayRecord",
]
