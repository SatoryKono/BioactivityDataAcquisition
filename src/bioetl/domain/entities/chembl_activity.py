"""ChEMBL bioactivity domain entities.

Contains Assay entity for bioassay definitions.

Field Classification:
    - REQUIRED: Validated in __post_init__, will raise ValueError if empty
    - API-OPTIONAL: May or may not be present in API response, defaults to None
    - COMPUTED: Derived from other fields, may be None if source data missing
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.base import BaseEntity
from bioetl.domain.entities.bioactivity import (
    Bioactivity,
    BioactivityState,
)

__all__ = [
    "Assay",
    "Bioactivity",
    "BioactivityState",
]


@dataclass(frozen=True, kw_only=True)
class Assay(BaseEntity):
    """Represents a bioassay definition (ChEMBL Assay).

    Contains all fields from ChEMBL assay API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/assay
    """

    # Primary identifier
    assay_id: str

    # Core identifiers
    target_id: str | None = None
    publication_id: str | None = None
    cell_id: str | None = None
    tissue_id: str | None = None
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
    # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
    assay_taxonomy_id: int | None = None
    assay_cell_type: str | None = None
    assay_tissue: str | None = None
    assay_strain: str | None = None
    assay_subcellular_fraction_raw: str | None = None
    assay_subcellular_fraction: str | None = None

    # BAO (BioAssay Ontology) annotations
    bao_format: str | None = None
    bao_format_iri: str | None = None
    bao_format_mapping_status: str | None = None
    bao_label: str | None = None
    bao_ontology_version: str | None = None

    # Description and confidence
    assay_description: str | None = None
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
    variant_sequence: str | None = None  # Amino amolecule_id sequence
    # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
    variant_taxonomy_id: int | None = None  # NCBI Taxonomy ID
    # NOTE: _json suffix retained — forensic raw dump, not a renamed business field
    variant_sequence_json: str | None = None

    # Complex fields (stored as JSON strings)
    assay_classifications: str | None = None  # JSON string of list
    assay_parameters: str | None = None  # JSON string of list

    def _validate_invariants(self) -> None:
        if not self.assay_id:
            raise ValueError("Assay ChEMBL ID is required")
        if self.confidence_score is not None and not (0 <= self.confidence_score <= 9):
            raise ValueError(
                f"Confidence score must be 0-9, got {self.confidence_score}"
            )
