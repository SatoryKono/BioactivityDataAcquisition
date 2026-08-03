"""UniProt domain entities.

Contains entities for UniProt data:
- UniprotTarget: Domain entity for protein targets
- IDMappingResult: ID mapping result entity
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bioetl.domain.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class IDMappingResult(BaseEntity):
    """Result of UniProt ID Mapping operation.

    Maps ChEMBL target IDs to UniProt accessions using UniProt ID Mapping REST API.
    Extracts comprehensive metadata from UniProt entries when mapping is found.

    Required fields: target_id, mapping_status
    Optional fields: All others (None if mapping not found or data unavailable)

    Attributes:
        target_id: Source ChEMBL target identifier (e.g., CHEMBL204)
        uniprot_accession: Mapped UniProt accession (e.g., P00742) or None if not found
        mapping_status: Status of mapping: 'found', 'not_found', 'error', 'multiple'
        uniprot_entry_name: UniProt entry name (e.g., FA10_HUMAN)
        organism_scientific: Scientific organism name (e.g., Homo sapiens)
        organism_common: Common organism name (e.g., Human)
        taxonomy_id: NCBI Taxonomy ID (e.g., 9606)
        protein_name: Recommended protein name
        gene_primary: Primary gene name
        sequence_length: Protein sequence length
        sequence_mass: Molecular weight in Daltons
        reviewed: True if Swiss-Prot (reviewed), False if TrEMBL (unreviewed)
        annotation_score: Quality score 1-5 (5 = best annotated)
        all_mappings: JSON array of all accessions when multiple mappings found
    """

    # Primary key (input)
    target_id: str

    # Core mapping result
    uniprot_accession: str | None = None
    mapping_status: Literal["found", "not_found", "error", "multiple"] = "not_found"

    # UniProt entry metadata
    uniprot_entry_name: str | None = None
    organism_scientific: str | None = None
    organism_common: str | None = None
    taxonomy_id: int | None = None
    protein_name: str | None = None
    gene_primary: str | None = None
    sequence_length: int | None = None
    sequence_mass: int | None = None
    reviewed: bool | None = None
    annotation_score: int | None = None

    # Multiple mappings (JSON array)
    all_mappings: str | None = None

    def _validate_invariants(self) -> None:
        """Validate domain-specific invariants."""
        if not self.target_id:
            raise ValueError("target_id is required")
        if self.mapping_status not in ("found", "not_found", "error", "multiple"):
            raise ValueError(
                f"Invalid mapping_status: {self.mapping_status}. "
                "Must be one of: 'found', 'not_found', 'error', 'multiple'"
            )
        # If status is 'found' or 'multiple', accession should be present
        if self.mapping_status in ("found", "multiple") and not self.uniprot_accession:
            raise ValueError(
                "uniprot_accession is required when mapping_status is 'found' or 'multiple'"
            )
        self._validate_annotation_score()
        self._validate_sequence_fields()

    def _validate_annotation_score(self) -> None:
        """Validate annotation_score is 1-5 if present."""
        if self.annotation_score is not None and not 1 <= self.annotation_score <= 5:
            raise ValueError(
                f"annotation_score must be 1-5, got {self.annotation_score}"
            )

    def _validate_sequence_fields(self) -> None:
        """Validate sequence_length and sequence_mass are positive if present."""
        if self.sequence_length is not None and self.sequence_length <= 0:
            raise ValueError(
                f"sequence_length must be positive, got {self.sequence_length}"
            )
        if self.sequence_mass is not None and self.sequence_mass <= 0:
            raise ValueError(
                f"sequence_mass must be positive, got {self.sequence_mass}"
            )


@dataclass(frozen=True, kw_only=True)
class UniprotTarget(BaseEntity):
    """Represents a protein target (UniProt).

    In the bioactivity domain, proteins are typically biological targets.

    Extended entity with comprehensive UniProt data including:
    - Core identifiers (accession, entry_name, entry_type)
    - Protein names (recommended, short, alternative, EC numbers)
    - Gene information (primary, synonyms, ORF names)
    - Organism and taxonomy
    - Evidence and quality metrics
    - Sequence information
    - Functional annotations (comments)
    - Cross-references (GO, DrugBank, ChEMBL, GtoPdb)
    - Features and keywords

    Required fields: accession, entry_name
    All other fields are optional.
    """

    # Core identifiers
    accession: str
    entry_name: str
    entry_type: str | None = None
    secondary_accessions: str | None = None  # JSON array

    # Protein names
    protein_name: str | None = None
    protein_short_names: str | None = None  # JSON array
    protein_alternative_names: str | None = None  # JSON array
    protein_ec_numbers: str | None = None  # JSON array
    flag: str | None = None  # Fragment/Precursor

    # Gene names
    gene_primary: str | None = None
    gene_synonyms: str | None = None  # JSON array
    gene_orf_names: str | None = None  # JSON array

    # Organism
    organism_scientific: str | None = None
    organism_common: str | None = None
    taxonomy_id: int | None = None
    lineage: str | None = None  # JSON array

    # Evidence & Quality
    protein_existence: str | None = None
    annotation_score: int | None = None
    reviewed: bool = False

    # Sequence
    sequence: str | None = None
    sequence_length: int | None = None
    sequence_mass: int | None = None
    sequence_checksum: str | None = None
    sequence_modified: str | None = None  # ISO date

    # Entry metadata
    entry_version: int | None = None
    entry_created: str | None = None  # ISO date
    entry_modified: str | None = None  # ISO date

    # Functional annotations (JSON arrays)
    function_comment: str | None = None
    catalytic_activity: str | None = None
    activity_regulation: str | None = None
    subunit: str | None = None
    pathway: str | None = None
    subcellular_location: str | None = None
    tissue_specificity: str | None = None
    alternative_products: str | None = None
    alternative_products_raw_json: str | None = None
    alternative_products_canonical_json: str | None = None
    disease_involvement: str | None = None
    pharmaceutical_use: str | None = None
    similarity_comment: str | None = None
    caution: str | None = None

    # Biochemical properties (JSON)
    cofactors: str | None = None  # JSON array of cofactors with name and ChEBI ID
    cofactors_raw_json: str | None = None
    cofactors_canonical_json: str | None = None
    biophysicochemical_properties: str | None = (
        None  # JSON object with pH, temp, kinetics
    )
    biophysicochemical_properties_raw_json: str | None = None
    biophysicochemical_properties_canonical_json: str | None = None
    induction: str | None = None  # JSON array of induction conditions

    # Cross-references (JSON arrays)
    go_terms: str | None = None
    drugbank_ids: str | None = None
    chembl_ids: str | None = None
    guidetopharmacology_ids: str | None = None
    pdb_xrefs: str | None = None  # JSON array of PDB cross-references
    interpro_xrefs: str | None = None  # JSON array of InterPro domain entries
    pfam_xrefs: str | None = None  # JSON array of Pfam family entries
    reactome_xrefs: str | None = None  # JSON array of Reactome pathway entries

    # Features & Keywords (JSON arrays)
    features_canonical_json: str | None = None  # Canonical JSON companion
    features_json: str | None = None  # All features combined (forensic)
    features_raw_json: str | None = None  # Raw provider JSON companion
    domains: str | None = None  # ft_domain features
    binding_sites: str | None = None  # ft_binding features
    active_sites: str | None = None  # ft_act_site features
    keywords: str | None = None

    # Taxonomy components (parsed from lineage)
    superkingdom: str | None = None
    phylum: str | None = None
    genus: str | None = None

    # GO components (filtered by aspect)
    molecular_function: str | None = None  # JSON array, aspect F
    cellular_component: str | None = None  # JSON array, aspect C

    # Structural features
    topology: str | None = None  # JSON array
    transmembrane: str | None = None  # JSON array
    intramembrane: str | None = None  # JSON array
    signal_peptide: str | None = None  # JSON array
    propeptide: str | None = None  # JSON array

    # PTM features
    glycosylation: str | None = None  # JSON array
    lipidation: str | None = None  # JSON array
    disulfide_bond: str | None = None  # JSON array
    modified_residue: str | None = None  # JSON array
    phosphorylation: str | None = None  # JSON array
    acetylation: str | None = None  # JSON array
    ubiquitination: str | None = None  # JSON array

    # Isoform details (parsed from ALTERNATIVE PRODUCTS)
    isoform_names: str | None = None  # JSON array
    isoform_ids: str | None = None  # JSON array
    isoform_synonyms: str | None = None  # JSON array

    # Reaction data (parsed from CATALYTIC ACTIVITY)
    reactions: str | None = None  # JSON array
    reactions_raw_json: str | None = None
    reactions_canonical_json: str | None = None
    reaction_ec_numbers: str | None = None  # JSON array

    # Counts
    cross_reference_count: int | None = None
    feature_count: int | None = None
    keyword_count: int | None = None
    publication_count: int | None = None
    isoform_count: int | None = None

    def _validate_invariants(self) -> None:
        if not self.accession:
            raise ValueError("UniprotTarget accession is required")
        if not self.entry_name:
            raise ValueError("UniprotTarget entry_name is required")
        self._validate_sequence_length()
        self._validate_annotation_score()

    def _validate_sequence_length(self) -> None:
        """Validate sequence_length is positive if present."""
        if self.sequence_length is not None and self.sequence_length <= 0:
            raise ValueError(
                f"Sequence length must be positive, got {self.sequence_length}"
            )

    def _validate_annotation_score(self) -> None:
        """Validate annotation_score is 1-5 if present."""
        if self.annotation_score is not None and not 1 <= self.annotation_score <= 5:
            raise ValueError(
                f"Annotation score must be 1-5, got {self.annotation_score}"
            )


__all__ = [
    "IDMappingResult",
    "UniprotTarget",
]
