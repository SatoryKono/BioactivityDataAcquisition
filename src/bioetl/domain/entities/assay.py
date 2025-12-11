"""Assay domain entity.

Represents a biological assay from ChEMBL database.
An Assay describes the experimental procedure used to measure
the activity of compounds against targets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

from bioetl.domain.entities.base import EntityBase, extract_field
from bioetl.domain.value_objects import ChemblId


@dataclass(frozen=True)
class Assay(EntityBase):
    """Domain entity representing a biological assay.

    An Assay encapsulates information about the experimental method
    used to measure compound activity, including the target, organism,
    and assay conditions.

    Attributes:
        assay_chembl_id: Unique ChEMBL assay identifier (primary key).
        assay_type: Type of assay (B=binding, F=functional, A=ADMET, etc.).
        assay_type_description: Human-readable assay type description.
        description: Full textual description of the assay.
        target_chembl_id: ChEMBL ID of the assay target.
        document_chembl_id: ChEMBL ID of the source document.
        confidence_score: Target mapping confidence (0-9).
        bao_format: BioAssay Ontology format identifier.

    Business Key:
        The business key is (assay_chembl_id) as it's the unique identifier.

    Example:
        >>> assay = Assay.from_record({
        ...     'assay_chembl_id': 'CHEMBL1000',
        ...     'assay_type': 'B',
        ...     'description': 'Binding assay for target X',
        ...     'target_chembl_id': 'CHEMBL123',
        ... })
    """

    # Primary identifier
    assay_chembl_id: str

    # Assay classification
    assay_type: str
    assay_type_description: str | None = None
    assay_category: str | None = None
    assay_test_type: str | None = None

    # Description and metadata
    description: str | None = None
    aidx: str | None = None
    assay_group: str | None = None

    # Target information
    target_chembl_id: str | None = None
    relationship_type: str | None = None
    relationship_description: str | None = None
    confidence_score: int | None = None
    confidence_description: str | None = None

    # Document reference
    document_chembl_id: str | None = None

    # Organism and biological context
    assay_organism: str | None = None
    assay_strain: str | None = None
    assay_tax_id: int | None = None
    assay_tissue: str | None = None
    assay_cell_type: str | None = None
    assay_subcellular_fraction: str | None = None

    # Cell and tissue references
    cell_chembl_id: str | None = None
    tissue_chembl_id: str | None = None

    # Ontology references
    bao_format: str | None = None
    bao_label: str | None = None

    # Source information
    src_id: int | None = None
    src_assay_id: str | None = None

    # Extended data (JSON serialized)
    assay_classifications: str | None = None
    assay_parameters: str | None = None
    variant_sequence: str | None = None

    # Search relevance
    score: float | None = None

    # Class configuration
    BUSINESS_KEY_FIELDS: ClassVar[tuple[str, ...]] = ("assay_chembl_id",)
    PRIMARY_KEY_FIELD: ClassVar[str] = "assay_chembl_id"

    def __post_init__(self) -> None:
        """Validate entity invariants."""
        # Validate ChEMBL ID format
        if not self.assay_chembl_id.startswith("CHEMBL"):
            raise ValueError(
                f"Invalid assay_chembl_id format: {self.assay_chembl_id}"
            )

        # Validate assay_type is one of allowed values
        allowed_assay_types = {"B", "F", "A", "T", "P", "U", "b", "f", "a", "t", "p", "u"}
        if self.assay_type not in allowed_assay_types:
            raise ValueError(
                f"Invalid assay_type: {self.assay_type}. "
                f"Must be one of: {allowed_assay_types}"
            )

        # Validate confidence_score range if present
        if self.confidence_score is not None:
            if not 0 <= self.confidence_score <= 9:
                raise ValueError(
                    f"confidence_score must be between 0 and 9, got {self.confidence_score}"
                )

    @property
    def chembl_id(self) -> ChemblId:
        """Return assay ID as ChemblId value object."""
        return ChemblId(self.assay_chembl_id)

    @property
    def is_binding_assay(self) -> bool:
        """Check if this is a binding assay."""
        return self.assay_type.upper() == "B"

    @property
    def is_functional_assay(self) -> bool:
        """Check if this is a functional assay."""
        return self.assay_type.upper() == "F"

    @property
    def is_admet_assay(self) -> bool:
        """Check if this is an ADMET assay."""
        return self.assay_type.upper() == "A"

    @property
    def has_high_confidence_target(self) -> bool:
        """Check if assay has high confidence target mapping (score >= 7)."""
        return self.confidence_score is not None and self.confidence_score >= 7

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Assay":
        """Create Assay from raw record dictionary.

        Args:
            record: Dictionary from API response or database.

        Returns:
            Assay entity instance.

        Raises:
            ValueError: If required fields are missing.
        """
        return cls(
            # Required fields
            assay_chembl_id=extract_field(record, "assay_chembl_id", required=True),
            assay_type=extract_field(record, "assay_type", required=True),
            # Classification
            assay_type_description=extract_field(record, "assay_type_description"),
            assay_category=extract_field(record, "assay_category"),
            assay_test_type=extract_field(record, "assay_test_type"),
            # Description
            description=extract_field(record, "description"),
            aidx=extract_field(record, "aidx"),
            assay_group=extract_field(record, "assay_group"),
            # Target
            target_chembl_id=extract_field(record, "target_chembl_id"),
            relationship_type=extract_field(record, "relationship_type"),
            relationship_description=extract_field(record, "relationship_description"),
            confidence_score=extract_field(record, "confidence_score", coerce=int),
            confidence_description=extract_field(record, "confidence_description"),
            # Document
            document_chembl_id=extract_field(record, "document_chembl_id"),
            # Biological context
            assay_organism=extract_field(record, "assay_organism"),
            assay_strain=extract_field(record, "assay_strain"),
            assay_tax_id=extract_field(record, "assay_tax_id", coerce=int),
            assay_tissue=extract_field(record, "assay_tissue"),
            assay_cell_type=extract_field(record, "assay_cell_type"),
            assay_subcellular_fraction=extract_field(record, "assay_subcellular_fraction"),
            # Cell and tissue refs
            cell_chembl_id=extract_field(record, "cell_chembl_id"),
            tissue_chembl_id=extract_field(record, "tissue_chembl_id"),
            # Ontology
            bao_format=extract_field(record, "bao_format"),
            bao_label=extract_field(record, "bao_label"),
            # Source
            src_id=extract_field(record, "src_id", coerce=int),
            src_assay_id=extract_field(record, "src_assay_id"),
            # Extended data
            assay_classifications=extract_field(record, "assay_classifications"),
            assay_parameters=extract_field(record, "assay_parameters"),
            variant_sequence=extract_field(record, "variant_sequence"),
            # Score
            score=extract_field(record, "score", coerce=float),
        )


__all__ = ["Assay"]
