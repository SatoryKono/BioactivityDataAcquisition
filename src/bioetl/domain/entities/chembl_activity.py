"""ChEMBL bioactivity domain entities.

Contains Activity and Assay entities for ChEMBL bioactivity data.

Field Classification:
- REQUIRED: Validated in __post_init__, will raise ValueError if empty
- API-OPTIONAL: May or may not be present in API response, defaults to None
- COMPUTED: Derived from other fields, may be None if source data missing
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class Activity(BaseEntity):
    """Represents a bioactivity measurement (ChEMBL Activity).

    Contains all fields from ChEMBL activity API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/activity

    Required Fields (validated):
        activity_id: Primary identifier (from BaseEntity fields + this)
        molecule_chembl_id: Molecule identifier (required for drug discovery)
        + All BaseEntity fields (entity_id, content_hash, run_id, etc.)

    API-Optional Fields:
        All other fields may be None depending on the activity record.
        Gold layer filters should be used to ensure required fields for analysis.

    Validation:
        - activity_id and molecule_chembl_id must be non-empty
        - pchembl_value must be non-negative if present
    """

    # REQUIRED: Primary identifier (validated in __post_init__)
    activity_id: str

    # REQUIRED: Core identifiers (validated in __post_init__)
    molecule_chembl_id: str
    target_chembl_id: str | None = None
    assay_chembl_id: str | None = None
    document_chembl_id: str | None = None
    record_id: int | None = None
    src_id: int | None = None

    # Molecule data
    canonical_smiles: str | None = None
    molecule_pref_name: str | None = None
    parent_molecule_chembl_id: str | None = None

    # Target data
    target_pref_name: str | None = None
    target_organism: str | None = None
    target_tax_id: str | None = None

    # Assay data
    assay_type: str | None = None
    assay_description: str | None = None
    assay_variant_accession: str | None = None
    assay_variant_mutation: str | None = None

    # BAO (BioAssay Ontology) annotations
    bao_endpoint: str | None = None
    bao_format: str | None = None
    bao_label: str | None = None

    # Raw activity values
    type: str | None = None
    value: float | None = None
    units: str | None = None
    relation: str | None = None
    upper_value: float | None = None
    text_value: str | None = None

    # Standardized activity values
    standard_type: str | None = None
    standard_value: float | None = None
    standard_units: str | None = None
    standard_relation: str | None = None
    standard_upper_value: float | None = None
    standard_text_value: str | None = None
    standard_flag: int | None = None

    # Derived metrics
    pchembl_value: float | None = None

    # Ligand efficiency metrics (flattened from ChEMBL API dict)
    ligand_efficiency_bei: float | None = None  # Binding Efficiency Index
    ligand_efficiency_le: float | None = None  # Ligand Efficiency
    ligand_efficiency_lle: float | None = None  # Lipophilic Ligand Efficiency
    ligand_efficiency_sei: float | None = None  # Surface Efficiency Index

    # Units ontology
    qudt_units: str | None = None
    uo_units: str | None = None

    # Document/Publication data
    document_journal: str | None = None
    document_year: int | None = None

    # Quality annotations
    activity_comment: str | None = None
    data_validity_comment: str | None = None
    data_validity_description: str | None = None
    potential_duplicate: int | None = None

    # Action type (flattened from ChEMBL API nested structure)
    action_type_action_type: str | None = (
        None  # Type of action (INHIBITOR, AGONIST, etc.)
    )
    action_type_description: str | None = None  # Description of the action type
    action_type_parent_type: str | None = None  # Higher-level grouping (nullable)

    # Activity properties
    activity_properties: str | None = None  # JSON string of list
    toid: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.activity_id:
            raise ValueError("Activity ID is required")
        if not self.molecule_chembl_id:
            raise ValueError("Molecule ID is required")
        self._validate_pchembl_value()

    def _validate_pchembl_value(self) -> None:
        """Validate pchembl_value is non-negative if present."""
        if self.pchembl_value is not None and self.pchembl_value < 0:
            raise ValueError(
                f"pChemBL value must be non-negative, got {self.pchembl_value}"
            )


@dataclass(frozen=True, kw_only=True)
class Assay(BaseEntity):
    """Represents a bioassay definition (ChEMBL Assay).

    Contains all fields from ChEMBL assay API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/assay
    """

    # Primary identifier
    assay_chembl_id: str

    # Core identifiers
    target_chembl_id: str | None = None
    document_chembl_id: str | None = None
    cell_chembl_id: str | None = None
    tissue_chembl_id: str | None = None
    src_id: int | None = None
    src_assay_id: str | None = None
    aidx: str | None = None

    # Assay classification
    assay_type: str | None = None
    assay_type_description: str | None = None
    assay_category: str | None = None
    assay_test_type: str | None = None
    assay_group: str | None = None

    # Biological context
    assay_organism: str | None = None
    assay_tax_id: int | None = None
    assay_cell_type: str | None = None
    assay_tissue: str | None = None
    assay_strain: str | None = None
    assay_subcellular_fraction: str | None = None

    # BAO (BioAssay Ontology) annotations
    bao_format: str | None = None
    bao_label: str | None = None

    # Description and confidence
    description: str | None = None
    confidence_score: int | None = None
    confidence_description: str | None = None
    relationship_type: str | None = None
    relationship_description: str | None = None

    # Additional metadata
    assay_pref_name: str | None = None  # Preferred assay name (if available)
    score: float | None = None  # Assay score (distinct from confidence_score)

    # Variant information (flattened from ChEMBL API nested structure)
    variant_accession: str | None = None  # UniProt accession
    variant_isoform: str | None = None  # Isoform identifier
    variant_mutation: str | None = None  # Mutation description (e.g., V600E)
    variant_organism: str | None = None  # Organism name
    variant_sequence: str | None = None  # Amino acid sequence
    variant_tax_id: int | None = None  # NCBI Taxonomy ID
    # Forensic: original JSON
    variant_sequence_json: str | None = None

    # Complex fields (stored as JSON strings)
    assay_classifications: str | None = None  # JSON string of list
    assay_parameters: str | None = None  # JSON string of list

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.assay_chembl_id:
            raise ValueError("Assay ChEMBL ID is required")
        if self.confidence_score is not None and not (0 <= self.confidence_score <= 9):
            raise ValueError(
                f"Confidence score must be 0-9, got {self.confidence_score}"
            )
