"""Molecule domain entity.

Represents a chemical compound from ChEMBL database.
A Molecule is a chemical entity that is tested in assays for biological activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

from bioetl.domain.entities.base import EntityBase, extract_field
from bioetl.domain.value_objects import ChemblId


@dataclass(frozen=True)
class Molecule(EntityBase):
    """Domain entity representing a chemical compound.

    A Molecule encapsulates information about a chemical entity,
    including its structure, properties, and drug development status.

    Attributes:
        molecule_chembl_id: Unique ChEMBL molecule identifier (primary key).
        molecule_type: Type of molecule (Small molecule, Protein, etc.).
        pref_name: Preferred molecule name.
        max_phase: Maximum clinical trial phase (0-4).
        first_approval: Year of first regulatory approval.

    Business Key:
        The business key is (molecule_chembl_id) as it's the unique identifier.

    Example:
        >>> molecule = Molecule.from_record({
        ...     'molecule_chembl_id': 'CHEMBL25',
        ...     'molecule_type': 'Small molecule',
        ...     'pref_name': 'ASPIRIN',
        ...     'max_phase': 4,
        ... })
    """

    # Primary identifier
    molecule_chembl_id: str

    # Classification
    molecule_type: str | None = None
    pref_name: str | None = None
    structure_type: str | None = None

    # Drug development status
    max_phase: float | None = None
    first_approval: int | None = None
    first_in_class: int | None = None
    therapeutic_flag: bool | None = None

    # Availability and warnings
    availability_type: int | None = None
    black_box_warning: int | None = None
    withdrawn_flag: bool | None = None

    # Molecule flags
    natural_product: int | None = None
    prodrug: int | None = None
    oral: bool | None = None
    parenteral: bool | None = None
    topical: bool | None = None
    veterinary: int | None = None
    chemical_probe: int | None = None
    orphan: int | None = None
    inorganic_flag: int | None = None
    polymer_flag: int | None = None
    dosed_ingredient: bool | None = None
    chirality: int | None = None

    # USAN nomenclature
    usan_stem: str | None = None
    usan_stem_definition: str | None = None
    usan_substem: str | None = None
    usan_year: int | None = None

    # Extended data (JSON serialized)
    molecule_properties: str | None = None
    molecule_structures: str | None = None
    molecule_hierarchy: str | None = None
    molecule_synonyms: str | None = None
    atc_classifications: str | None = None
    cross_references: str | None = None

    # Structural notation
    helm_notation: str | None = None

    # Class configuration
    BUSINESS_KEY_FIELDS: ClassVar[tuple[str, ...]] = ("molecule_chembl_id",)
    PRIMARY_KEY_FIELD: ClassVar[str] = "molecule_chembl_id"

    def __post_init__(self) -> None:
        """Validate entity invariants."""
        # Validate ChEMBL ID format
        if not self.molecule_chembl_id.startswith("CHEMBL"):
            raise ValueError(
                f"Invalid molecule_chembl_id format: {self.molecule_chembl_id}"
            )

        # Validate max_phase range if present
        if self.max_phase is not None:
            if not 0 <= self.max_phase <= 4:
                raise ValueError(
                    f"max_phase must be between 0 and 4, got {self.max_phase}"
                )

    @property
    def chembl_id(self) -> ChemblId:
        """Return molecule ID as ChemblId value object."""
        return ChemblId(self.molecule_chembl_id)

    @property
    def is_small_molecule(self) -> bool:
        """Check if this is a small molecule."""
        return self.molecule_type == "Small molecule"

    @property
    def is_approved_drug(self) -> bool:
        """Check if molecule is an approved drug (phase 4)."""
        return self.max_phase is not None and self.max_phase >= 4

    @property
    def is_in_clinical_trials(self) -> bool:
        """Check if molecule is in clinical trials (phase 1-3)."""
        return self.max_phase is not None and 1 <= self.max_phase < 4

    @property
    def has_black_box_warning(self) -> bool:
        """Check if molecule has black box warning."""
        return self.black_box_warning == 1

    @property
    def is_withdrawn(self) -> bool:
        """Check if molecule is withdrawn."""
        return self.withdrawn_flag is True

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Molecule":
        """Create Molecule from raw record dictionary.

        Args:
            record: Dictionary from API response or database.

        Returns:
            Molecule entity instance.

        Raises:
            ValueError: If required fields are missing.
        """
        return cls(
            # Required fields
            molecule_chembl_id=extract_field(
                record, "molecule_chembl_id", required=True
            ),
            # Classification
            molecule_type=extract_field(record, "molecule_type"),
            pref_name=extract_field(record, "pref_name"),
            structure_type=extract_field(record, "structure_type"),
            # Drug status
            max_phase=extract_field(record, "max_phase", coerce=float),
            first_approval=extract_field(record, "first_approval", coerce=int),
            first_in_class=extract_field(record, "first_in_class", coerce=int),
            therapeutic_flag=extract_field(record, "therapeutic_flag"),
            # Availability
            availability_type=extract_field(record, "availability_type", coerce=int),
            black_box_warning=extract_field(record, "black_box_warning", coerce=int),
            withdrawn_flag=extract_field(record, "withdrawn_flag"),
            # Molecule flags
            natural_product=extract_field(record, "natural_product", coerce=int),
            prodrug=extract_field(record, "prodrug", coerce=int),
            oral=extract_field(record, "oral"),
            parenteral=extract_field(record, "parenteral"),
            topical=extract_field(record, "topical"),
            veterinary=extract_field(record, "veterinary", coerce=int),
            chemical_probe=extract_field(record, "chemical_probe", coerce=int),
            orphan=extract_field(record, "orphan", coerce=int),
            inorganic_flag=extract_field(record, "inorganic_flag", coerce=int),
            polymer_flag=extract_field(record, "polymer_flag", coerce=int),
            dosed_ingredient=extract_field(record, "dosed_ingredient"),
            chirality=extract_field(record, "chirality", coerce=int),
            # USAN
            usan_stem=extract_field(record, "usan_stem"),
            usan_stem_definition=extract_field(record, "usan_stem_definition"),
            usan_substem=extract_field(record, "usan_substem"),
            usan_year=extract_field(record, "usan_year", coerce=int),
            # Extended data
            molecule_properties=extract_field(record, "molecule_properties"),
            molecule_structures=extract_field(record, "molecule_structures"),
            molecule_hierarchy=extract_field(record, "molecule_hierarchy"),
            molecule_synonyms=extract_field(record, "molecule_synonyms"),
            atc_classifications=extract_field(record, "atc_classifications"),
            cross_references=extract_field(record, "cross_references"),
            # Structural
            helm_notation=extract_field(record, "helm_notation"),
        )


__all__ = ["Molecule"]
