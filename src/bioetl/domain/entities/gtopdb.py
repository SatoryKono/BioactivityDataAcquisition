"""GtoPdb (Guide to Pharmacology) domain entities.

Contains entities for GtoPdb data: GtopdbTarget, GtopdbLigand.
See: https://www.guidetopharmacology.org/webServices.jsp
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class GtopdbTarget(BaseEntity):
    """Represents a pharmacological target from GtoPdb.

    Field Classification:
    - REQUIRED: target_id (primary identifier)
    - API-OPTIONAL: All other fields (may be None depending on API response)

    See: https://www.guidetopharmacology.org/services/targets
    """

    # Primary identifier (REQUIRED)
    target_id: int

    # Core metadata
    name: str | None = None
    abbreviation: str | None = None
    systematic_name: str | None = None
    target_type: str | None = None  # e.g., "gpcr", "lgic", "vgic", "enzyme"

    # Family hierarchy
    family_id: int | None = None
    family_name: str | None = None
    family_ids: str | None = None  # JSON list of family IDs

    # Species information
    species: str | None = None  # e.g., "Human", "Mouse", "Rat"
    species_id: int | None = None  # NCBI taxonomy ID

    # Gene information
    gene_symbol: str | None = None
    gene_id: int | None = None  # Entrez gene ID
    ensembl_gene_id: str | None = None

    # UniProt cross-references
    uniprot_ids: str | None = None  # JSON list of UniProt accessions

    # Additional identifiers
    hgnc_id: int | None = None
    hgnc_symbol: str | None = None
    hgnc_name: str | None = None

    # Nomenclature
    nomenclature_status: str | None = None  # e.g., "approved", "tentative"

    def __post_init__(self) -> None:
        """Validate required fields."""
        super().__post_init__()
        if not self.target_id:
            raise ValueError("GtoPdb Target ID is required")


@dataclass(frozen=True, kw_only=True)
class GtopdbLigand(BaseEntity):
    """Represents a ligand from GtoPdb.

    Field Classification:
    - REQUIRED: ligand_id (primary identifier)
    - API-OPTIONAL: All other fields (may be None depending on API response)

    See: https://www.guidetopharmacology.org/services/ligands
    """

    # Primary identifier (REQUIRED)
    ligand_id: int

    # Core metadata
    name: str | None = None
    ligand_type: str | None = None  # e.g., "Synthetic organic", "Peptide", "Antibody"
    approved: bool | None = None
    withdrawn: bool | None = None
    labelled: bool | None = None
    radioactive: bool | None = None

    # Structural information
    smiles: str | None = None
    inchi: str | None = None
    inchi_key: str | None = None
    iupac_name: str | None = None

    # Drug status
    inn: str | None = None  # International Nonproprietary Name
    approved_source: str | None = None  # e.g., "FDA", "EMA"

    # Species (for peptides/proteins)
    species: str | None = None

    # Cross-references
    pubchem_sid: int | None = None
    pubchem_cid: int | None = None
    chembl_id: str | None = None
    drugbank_id: str | None = None
    cas_number: str | None = None

    # Comments and descriptions
    comments: str | None = None

    def __post_init__(self) -> None:
        """Validate required fields."""
        super().__post_init__()
        if not self.ligand_id:
            raise ValueError("GtoPdb Ligand ID is required")


@dataclass(frozen=True, kw_only=True)
class GtopdbInteraction(BaseEntity):
    """Represents a target-ligand interaction from GtoPdb.

    Field Classification:
    - REQUIRED: interaction_id, target_id, ligand_id
    - API-OPTIONAL: All other fields

    See: https://www.guidetopharmacology.org/services/interactions
    """

    # Primary identifier
    interaction_id: int

    # Foreign keys (REQUIRED for meaningful interaction)
    target_id: int
    ligand_id: int

    # Interaction type
    interaction_type: str | None = None  # e.g., "Agonist", "Antagonist", "Inhibitor"
    action: str | None = None  # e.g., "Activation", "Inhibition"
    action_comment: str | None = None
    selectivity: str | None = None  # e.g., "Selective", "Non-selective"

    # Affinity data
    affinity_type: str | None = None  # e.g., "pKi", "pIC50", "pEC50"
    affinity_value: float | None = None
    affinity_low: float | None = None
    affinity_high: float | None = None
    affinity_median: float | None = None
    affinity_units: str | None = None
    affinity_qualifier: str | None = None  # e.g., "=", "<", ">"

    # Species context
    species: str | None = None
    species_id: int | None = None

    # Endogenous ligand flag
    endogenous: bool | None = None
    primary_target: bool | None = None

    # References
    pubmed_ids: str | None = None  # JSON list

    def __post_init__(self) -> None:
        """Validate required fields."""
        super().__post_init__()
        if not self.interaction_id:
            raise ValueError("GtoPdb Interaction ID is required")
        if not self.target_id:
            raise ValueError("Target ID is required for interaction")
        if not self.ligand_id:
            raise ValueError("Ligand ID is required for interaction")
