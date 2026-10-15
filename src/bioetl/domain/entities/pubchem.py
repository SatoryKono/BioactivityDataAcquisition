# mypy: disable-error-code="misc"
"""PubChem domain entities.

Contains:
- PubchemMolecule: Domain entity (dataclass) with lineage fields
- PubchemMoleculeRecord: DTO (Pydantic) for type-safe data transfer at boundaries

DTO Design:
- Uses extra='forbid' to detect API changes early
- frozen=True ensures immutability
- Adapters return DTOs, transformers convert to Domain Entities
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.entities.base import BaseEntity

# === Pydantic DTO Model ===


class PubchemMoleculeRecord(BaseModel):
    """Chemical molecule DTO from PubChem.

    Represents a molecule (compound) from PubChem API via pubchempy.
    Required field: molecule_id.
    At least one structural identifier (SMILES/InChI) should be present.

    Contains all physicochemical properties defined in PubchemMoleculeSchema:
    - Structural identifiers (SMILES, InChI, InChI Key)
    - Nomenclature (molecular formula, IUPAC name)
    - Physical properties (molecular weight, exact mass)
    - Computed descriptors (XLogP, TPSA, complexity, charge)
    - Atom/Bond counts (heavy atoms, H-bond donors/acceptors, rotatable bonds)
    - Stereochemistry (atom/bond stereo counts)
    - 3D properties (volume, conformer count, feature counts)

    Example:
        >>> record = PubchemMoleculeRecord(
        ...     molecule_id="2244",
        ...     molecular_formula="C9H8O4",
        ...     canonical_smiles="CC(=O)OC1=CC=CC=C1C(=O)O",
        ... )
        >>> record.model_dump()
        {'molecule_id': '2244', 'molecular_formula': 'C9H8O4', ...}
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # === Primary Identifier (REQUIRED) ===
    molecule_id: str = Field(description="PubChem Compound ID")

    # === Structural Identifiers ===
    canonical_smiles: str | None = Field(
        default=None, description="Canonical SMILES (connectivity)"
    )
    isomeric_smiles: str | None = Field(
        default=None, description="Isomeric SMILES (with stereochemistry)"
    )
    inchi: str | None = Field(default=None, description="InChI string")
    inchi_key: str | None = Field(default=None, description="InChI Key")
    standardized_canonical_smiles: str | None = Field(
        default=None, description="Policy-normalized canonical SMILES"
    )
    standardized_isomeric_smiles: str | None = Field(
        default=None, description="Policy-normalized isomeric SMILES"
    )
    standardized_inchi: str | None = Field(
        default=None, description="Policy-normalized InChI string"
    )
    standardized_inchi_key: str | None = Field(
        default=None, description="Policy-normalized InChI Key"
    )
    structure_parent_key: str | None = Field(
        default=None, description="Stable parent-structure grouping key"
    )
    chemical_standardization_status: str | None = Field(
        default=None, description="Bounded chemical standardization status"
    )
    chemical_standardization_warnings: str | None = Field(
        default=None, description="JSON array of chemical standardization warnings"
    )
    chemical_standardization_policy_version: str | None = Field(
        default=None, description="Version of the applied standardization policy"
    )

    # === Nomenclature ===
    molecular_formula: str | None = Field(default=None, description="Molecular formula")
    iupac_name: str | None = Field(default=None, description="IUPAC systematic name")

    # === Physical Properties ===
    molecular_weight: float | None = Field(
        default=None, description="Molecular weight in g/mol"
    )
    exact_mass: float | None = Field(
        default=None, description="Monoisotopic exact mass (Da)"
    )
    monoisotopic_mass: float | None = Field(
        default=None, description="Monoisotopic mass using most abundant isotope (Da)"
    )

    # === Computed Descriptors ===
    xlogp: float | None = Field(
        default=None, description="Computed octanol-water partition coefficient"
    )
    tpsa: float | None = Field(
        default=None, description="Topological polar surface area (Å²)"
    )
    complexity: float | None = Field(
        default=None, description="Structural complexity score"
    )
    charge: int | None = Field(default=None, description="Formal charge")

    # === Atom/Bond Counts ===
    heavy_atom_count: int | None = Field(
        default=None, description="Non-hydrogen atom count"
    )
    h_bond_donor_count: int | None = Field(
        default=None, description="Hydrogen bond donor count"
    )
    h_bond_acceptor_count: int | None = Field(
        default=None, description="Hydrogen bond acceptor count"
    )
    rotatable_bond_count: int | None = Field(
        default=None, description="Rotatable bond count"
    )

    # === Stereochemistry ===
    atom_stereo_count: int | None = Field(
        default=None, description="Total stereocenters"
    )
    defined_atom_stereo_count: int | None = Field(
        default=None, description="Defined stereocenters"
    )
    undefined_atom_stereo_count: int | None = Field(
        default=None, description="Undefined stereocenters"
    )
    bond_stereo_count: int | None = Field(default=None, description="Total E/Z bonds")
    defined_bond_stereo_count: int | None = Field(
        default=None, description="Defined E/Z bonds"
    )
    undefined_bond_stereo_count: int | None = Field(
        default=None, description="Undefined E/Z bonds"
    )
    isotope_atom_count: int | None = Field(
        default=None, description="Isotopic atom count"
    )
    covalent_unit_count: int | None = Field(
        default=None, description="Number of covalent units"
    )

    # === 3D Properties ===
    volume_3d: float | None = Field(
        default=None, description="3D molecular volume (Å³)"
    )
    conformer_count_3d: int | None = Field(
        default=None, description="Number of 3D conformers"
    )
    feature_acceptor_count_3d: int | None = Field(
        default=None, description="3D H-bond acceptor features"
    )
    feature_donor_count_3d: int | None = Field(
        default=None, description="3D H-bond donor features"
    )
    feature_anion_count_3d: int | None = Field(
        default=None, description="3D anion features"
    )
    feature_cation_count_3d: int | None = Field(
        default=None, description="3D cation features"
    )
    feature_ring_count_3d: int | None = Field(
        default=None, description="3D ring features"
    )
    feature_hydrophobe_count_3d: int | None = Field(
        default=None, description="3D hydrophobic features"
    )
    effective_rotor_count_3d: float | None = Field(
        default=None, description="Effective rotatable bonds (3D)"
    )
    conformer_rmsd_3d: float | None = Field(
        default=None, description="Conformer model RMSD"
    )
    x_steric_quadrupole_3d: float | None = Field(
        default=None,
        description="X-axis steric quadrupole moment (3D charge distribution)",
    )
    y_steric_quadrupole_3d: float | None = Field(
        default=None,
        description="Y-axis steric quadrupole moment (3D charge distribution)",
    )
    z_steric_quadrupole_3d: float | None = Field(
        default=None,
        description="Z-axis steric quadrupole moment (3D charge distribution)",
    )
    feature_count_3d: int | None = Field(
        default=None, description="Total count of 3D pharmacophore features"
    )

    # === Fingerprints (not in schema, but available) ===
    fingerprint: str | None = Field(default=None, description="PubChem fingerprint")


# === Dataclass Domain Entity ===


@dataclass(frozen=True, kw_only=True)
class PubchemMolecule(BaseEntity):
    """Represents a chemical compound/molecule (PubChem Molecule).

    Domain entity with lineage fields (run_id, content_hash, etc.).
    For DTO without lineage, use PubchemMoleculeRecord.

    Contains all physicochemical properties defined in PubchemMoleculeSchema:
    - Structural identifiers (SMILES, InChI, InChI Key)
    - Nomenclature (molecular formula, IUPAC name)
    - Physical properties (molecular weight, exact mass)
    - Computed descriptors (XLogP, TPSA, complexity, charge)
    - Atom/Bond counts (heavy atoms, H-bond donors/acceptors, rotatable bonds)
    - Stereochemistry (atom/bond stereo counts)
    - 3D properties (volume, conformer count, feature counts)
    """

    # === Primary Identifier (REQUIRED) ===
    molecule_id: str

    # === Structural Identifiers ===
    canonical_smiles: str | None = None
    isomeric_smiles: str | None = None
    inchi: str | None = None
    inchi_key: str | None = None
    standardized_canonical_smiles: str | None = None
    standardized_isomeric_smiles: str | None = None
    standardized_inchi: str | None = None
    standardized_inchi_key: str | None = None
    structure_parent_key: str | None = None
    chemical_standardization_status: str | None = None
    chemical_standardization_warnings: str | None = None
    chemical_standardization_policy_version: str | None = None

    # === Nomenclature ===
    molecular_formula: str | None = None
    iupac_name: str | None = None

    # === Physical Properties ===
    molecular_weight: float | None = None
    exact_mass: float | None = None
    monoisotopic_mass: float | None = None

    # === Computed Descriptors ===
    xlogp: float | None = None
    tpsa: float | None = None
    complexity: float | None = None
    charge: int | None = None

    # === Atom/Bond Counts ===
    heavy_atom_count: int | None = None
    h_bond_donor_count: int | None = None
    h_bond_acceptor_count: int | None = None
    rotatable_bond_count: int | None = None

    # === Stereochemistry ===
    atom_stereo_count: int | None = None
    defined_atom_stereo_count: int | None = None
    undefined_atom_stereo_count: int | None = None
    bond_stereo_count: int | None = None
    defined_bond_stereo_count: int | None = None
    undefined_bond_stereo_count: int | None = None
    isotope_atom_count: int | None = None
    covalent_unit_count: int | None = None

    # === 3D Properties ===
    volume_3d: float | None = None
    conformer_count_3d: int | None = None
    feature_acceptor_count_3d: int | None = None
    feature_donor_count_3d: int | None = None
    feature_anion_count_3d: int | None = None
    feature_cation_count_3d: int | None = None
    feature_ring_count_3d: int | None = None
    feature_hydrophobe_count_3d: int | None = None
    effective_rotor_count_3d: float | None = None
    conformer_rmsd_3d: float | None = None
    x_steric_quadrupole_3d: float | None = None
    y_steric_quadrupole_3d: float | None = None
    z_steric_quadrupole_3d: float | None = None
    feature_count_3d: int | None = None

    def _validate_invariants(self) -> None:
        if not self.molecule_id:
            raise ValueError("PubchemMolecule molecule_id is required")

        # Invariant: At least one structural representation should be present
        if not any([self.canonical_smiles, self.isomeric_smiles, self.inchi]):
            raise ValueError(
                "PubchemMolecule must have at least one structural identifier "
                "(SMILES/InChI)"
            )


__all__ = [
    "PubchemMolecule",
    "PubchemMoleculeRecord",
]
