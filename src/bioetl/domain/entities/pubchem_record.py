# mypy: disable-error-code="misc"
"""PubChem DTO model."""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class PubchemMoleculeRecord(BaseModel):
    """Immutable PubChem DTO with strict boundary validation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pubchem_cid: str = Field(
        description="PubChem Compound ID",
        validation_alias=AliasChoices("pubchem_cid", "molecule_id"),
    )
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
    molecular_formula: str | None = Field(default=None, description="Molecular formula")
    iupac_name: str | None = Field(default=None, description="IUPAC systematic name")
    molecular_weight: float | None = Field(
        default=None, description="Molecular weight in g/mol"
    )
    exact_mass: float | None = Field(
        default=None, description="Monoisotopic exact mass (Da)"
    )
    monoisotopic_mass: float | None = Field(
        default=None, description="Monoisotopic mass using most abundant isotope (Da)"
    )
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
    fingerprint: str | None = Field(default=None, description="PubChem fingerprint")


__all__ = ["PubchemMolecule", "PubchemMoleculeRecord"]

# Backward compatibility alias
PubchemMolecule = PubchemMoleculeRecord
