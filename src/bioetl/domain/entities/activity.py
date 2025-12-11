"""Activity domain entity.

Represents a bioactivity measurement from ChEMBL database.
An Activity records the biological effect of a molecule on a target
as measured in an assay.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

from bioetl.domain.entities.base import EntityBase, extract_field
from bioetl.domain.value_objects import ActivityId, ChemblId


@dataclass(frozen=True)
class Activity(EntityBase):
    """Domain entity representing a bioactivity measurement.

    An Activity captures the relationship between a molecule and a target,
    including the assay conditions and measured values.

    Attributes:
        activity_id: Unique activity identifier (primary key).
        molecule_chembl_id: ChEMBL ID of the tested molecule.
        assay_chembl_id: ChEMBL ID of the assay used.
        target_chembl_id: ChEMBL ID of the biological target.
        document_chembl_id: ChEMBL ID of the source document.
        standard_type: Standardized activity type (e.g., 'IC50', 'Ki').
        standard_value: Standardized numeric value.
        standard_units: Standardized measurement units.
        standard_relation: Relation operator ('=', '<', '>', etc.).
        pchembl_value: Normalized -log10 activity value (0-15 range).
        assay_type: Type of assay (B=binding, F=functional).
        assay_description: Textual description of assay.
        action_type: Type of action (agonist, antagonist, etc.).
        target_pref_name: Preferred name of target.
        target_organism: Organism of the target.
        molecule_pref_name: Preferred name of molecule.
        canonical_smiles: Canonical SMILES representation.

    Business Key:
        The business key consists of (molecule_chembl_id, assay_chembl_id,
        standard_type, standard_value, standard_units) to identify unique
        activity measurements.

    Example:
        >>> activity = Activity.from_record({
        ...     'activity_id': 12345,
        ...     'molecule_chembl_id': 'CHEMBL123',
        ...     'assay_chembl_id': 'CHEMBL456',
        ...     'target_chembl_id': 'CHEMBL789',
        ...     'document_chembl_id': 'CHEMBL1000',
        ...     'standard_type': 'IC50',
        ...     'standard_value': 10.5,
        ...     'standard_units': 'nM',
        ... })
    """

    # Primary identifiers
    activity_id: int
    molecule_chembl_id: str
    assay_chembl_id: str
    target_chembl_id: str | None
    document_chembl_id: str

    # Standardized values
    standard_type: str | None
    standard_value: float | None
    standard_units: str | None
    standard_relation: str | None
    pchembl_value: float | None

    # Original values (for reference)
    type: str | None = None
    value: float | None = None
    units: str | None = None
    relation: str | None = None

    # Assay information
    assay_type: str | None = None
    assay_description: str | None = None

    # Action and target info
    action_type: str | None = None
    target_pref_name: str | None = None
    target_organism: str | None = None
    target_tax_id: int | None = None

    # Molecule info
    molecule_pref_name: str | None = None
    canonical_smiles: str | None = None
    parent_molecule_chembl_id: str | None = None

    # Document info
    document_journal: str | None = None
    document_year: int | None = None

    # Quality flags
    standard_flag: bool = True
    potential_duplicate: bool | None = None
    data_validity_comment: str | None = None
    data_validity_description: str | None = None
    activity_comment: str | None = None

    # Additional metadata
    bao_endpoint: str | None = None
    bao_format: str | None = None
    bao_label: str | None = None
    record_id: int | None = None
    src_id: int | None = None
    toid: str | None = None

    # Extended properties (JSON serialized)
    activity_properties: str | None = None
    ligand_efficiency: str | None = None

    # Variant information
    assay_variant_accession: str | None = None
    assay_variant_mutation: str | None = None

    # Additional value fields
    text_value: str | None = None
    standard_text_value: str | None = None
    upper_value: float | None = None
    standard_upper_value: float | None = None

    # Unit ontology
    qudt_units: str | None = None
    uo_units: str | None = None

    # Class configuration
    BUSINESS_KEY_FIELDS: ClassVar[tuple[str, ...]] = (
        "molecule_chembl_id",
        "assay_chembl_id",
        "standard_type",
        "standard_value",
        "standard_units",
    )
    PRIMARY_KEY_FIELD: ClassVar[str] = "activity_id"

    def __post_init__(self) -> None:
        """Validate entity invariants."""
        # Validate required ChEMBL IDs format
        if self.molecule_chembl_id and not self.molecule_chembl_id.startswith("CHEMBL"):
            raise ValueError(
                f"Invalid molecule_chembl_id format: {self.molecule_chembl_id}"
            )
        if self.assay_chembl_id and not self.assay_chembl_id.startswith("CHEMBL"):
            raise ValueError(f"Invalid assay_chembl_id format: {self.assay_chembl_id}")

        # Validate pchembl_value range if present
        if self.pchembl_value is not None:
            if not 0 <= self.pchembl_value <= 15:
                raise ValueError(
                    f"pchembl_value must be between 0 and 15, got {self.pchembl_value}"
                )

    @property
    def is_standardized(self) -> bool:
        """Check if activity has standardized values."""
        return self.standard_flag and self.standard_value is not None

    @property
    def has_potency(self) -> bool:
        """Check if activity has valid potency measurement."""
        return self.pchembl_value is not None

    @property
    def molecule_id(self) -> ChemblId:
        """Return molecule ID as ChemblId value object."""
        return ChemblId(self.molecule_chembl_id)

    @property
    def assay_id(self) -> ChemblId:
        """Return assay ID as ChemblId value object."""
        return ChemblId(self.assay_chembl_id)

    @property
    def primary_key_value(self) -> ActivityId:
        """Return activity ID as ActivityId value object."""
        return ActivityId(self.activity_id)

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Activity":
        """Create Activity from raw record dictionary.

        Args:
            record: Dictionary from API response or database.

        Returns:
            Activity entity instance.

        Raises:
            ValueError: If required fields are missing.
        """
        return cls(
            # Required fields
            activity_id=extract_field(record, "activity_id", required=True, coerce=int),
            molecule_chembl_id=extract_field(
                record, "molecule_chembl_id", required=True
            ),
            assay_chembl_id=extract_field(record, "assay_chembl_id", required=True),
            document_chembl_id=extract_field(
                record, "document_chembl_id", required=True
            ),
            # Optional identifiers
            target_chembl_id=extract_field(record, "target_chembl_id"),
            # Standardized values
            standard_type=extract_field(record, "standard_type"),
            standard_value=extract_field(record, "standard_value", coerce=float),
            standard_units=extract_field(record, "standard_units"),
            standard_relation=extract_field(record, "standard_relation"),
            pchembl_value=extract_field(record, "pchembl_value", coerce=float),
            # Original values
            type=extract_field(record, "type"),
            value=extract_field(record, "value", coerce=float),
            units=extract_field(record, "units"),
            relation=extract_field(record, "relation"),
            # Assay info
            assay_type=extract_field(record, "assay_type"),
            assay_description=extract_field(record, "assay_description"),
            # Action and target
            action_type=extract_field(record, "action_type"),
            target_pref_name=extract_field(record, "target_pref_name"),
            target_organism=extract_field(record, "target_organism"),
            target_tax_id=extract_field(record, "target_tax_id", coerce=int),
            # Molecule info
            molecule_pref_name=extract_field(record, "molecule_pref_name"),
            canonical_smiles=extract_field(record, "canonical_smiles"),
            parent_molecule_chembl_id=extract_field(
                record, "parent_molecule_chembl_id"
            ),
            # Document info
            document_journal=extract_field(record, "document_journal"),
            document_year=extract_field(record, "document_year", coerce=int),
            # Quality flags
            standard_flag=extract_field(record, "standard_flag", default=True),
            potential_duplicate=extract_field(record, "potential_duplicate"),
            data_validity_comment=extract_field(record, "data_validity_comment"),
            data_validity_description=extract_field(
                record, "data_validity_description"
            ),
            activity_comment=extract_field(record, "activity_comment"),
            # Metadata
            bao_endpoint=extract_field(record, "bao_endpoint"),
            bao_format=extract_field(record, "bao_format"),
            bao_label=extract_field(record, "bao_label"),
            record_id=extract_field(record, "record_id", coerce=int),
            src_id=extract_field(record, "src_id", coerce=int),
            toid=extract_field(record, "toid"),
            # Extended properties
            activity_properties=extract_field(record, "activity_properties"),
            ligand_efficiency=extract_field(record, "ligand_efficiency"),
            # Variant info
            assay_variant_accession=extract_field(record, "assay_variant_accession"),
            assay_variant_mutation=extract_field(record, "assay_variant_mutation"),
            # Additional values
            text_value=extract_field(record, "text_value"),
            standard_text_value=extract_field(record, "standard_text_value"),
            upper_value=extract_field(record, "upper_value", coerce=float),
            standard_upper_value=extract_field(
                record, "standard_upper_value", coerce=float
            ),
            # Unit ontology
            qudt_units=extract_field(record, "qudt_units"),
            uo_units=extract_field(record, "uo_units"),
        )


__all__ = ["Activity"]
