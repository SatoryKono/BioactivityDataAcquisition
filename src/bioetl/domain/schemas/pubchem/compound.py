"""Pandera schema for PubChem Compound entity.

Aligned with RULES.md v5.0 and PubChem PUG REST API.
Source: https://pubchem.ncbi.nlm.nih.gov/rest/pug/
"""

from __future__ import annotations

import pandera as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class CompoundSchema(ETLRecordSchema):
    """PubChem Compound validation schema for Silver layer.

    Represents a unique chemical structure identified by CID.
    """

    # === Primary Key ===
    cid: Series[int] = pa.Field(
        nullable=False, ge=1, description="PubChem Compound ID (PK)"
    )

    # === Structural Identifiers ===
    canonical_smiles: Series[str] | None = pa.Field(
        nullable=True,
        str_length={"max_value": 10000},
        description="Canonical SMILES string",
    )
    isomeric_smiles: Series[str] | None = pa.Field(
        nullable=True,
        str_length={"max_value": 10000},
        description="SMILES with stereochemistry",
    )
    inchi: Series[str] | None = pa.Field(
        nullable=True, str_startswith="InChI=", description="IUPAC InChI identifier"
    )
    inchi_key: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$",
        description="InChI hash key (27 chars)",
    )

    # === Nomenclature ===
    molecular_formula: Series[str] | None = pa.Field(
        nullable=True, description="Molecular formula (e.g., C6H12O6)"
    )
    iupac_name: Series[str] | None = pa.Field(
        nullable=True, description="IUPAC systematic name"
    )

    # === Physical Properties ===
    molecular_weight: Series[float] | None = pa.Field(
        nullable=True, ge=0, description="Average molecular weight (Da)"
    )
    exact_mass: Series[float] | None = pa.Field(
        nullable=True, ge=0, description="Monoisotopic exact mass (Da)"
    )

    # === Computed Descriptors ===
    xlogp: Series[float] | None = pa.Field(
        nullable=True,
        ge=-20,
        le=20,
        description="Computed octanol-water partition coefficient",
    )
    tpsa: Series[float] | None = pa.Field(
        nullable=True, ge=0, description="Topological polar surface area (Å²)"
    )
    complexity: Series[float] | None = pa.Field(
        nullable=True, ge=0, description="Structural complexity score"
    )
    charge: Series[int] | None = pa.Field(
        nullable=True, ge=-10, le=10, description="Formal charge"
    )

    # === Atom/Bond Counts ===
    heavy_atom_count: Series[int] | None = pa.Field(
        nullable=True, ge=1, le=500, description="Non-hydrogen atom count"
    )
    h_bond_donor_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, le=50, description="Hydrogen bond donor count"
    )
    h_bond_acceptor_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, le=50, description="Hydrogen bond acceptor count"
    )
    rotatable_bond_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, le=100, description="Rotatable bond count"
    )

    # === Stereochemistry ===
    atom_stereo_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Total stereocenters"
    )
    defined_atom_stereo_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Defined stereocenters"
    )
    undefined_atom_stereo_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Undefined stereocenters"
    )
    bond_stereo_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Total E/Z bonds"
    )
    defined_bond_stereo_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Defined E/Z bonds"
    )
    undefined_bond_stereo_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Undefined E/Z bonds"
    )
    isotope_atom_count: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Isotopic atom count"
    )
    covalent_unit_count: Series[int] | None = pa.Field(
        nullable=True, ge=1, description="Number of covalent units"
    )

    # === 3D Properties ===
    volume_3d: Series[float] | None = pa.Field(
        nullable=True, ge=0, description="3D molecular volume (Å³)"
    )
    conformer_count_3d: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="Number of 3D conformers"
    )
    feature_acceptor_count_3d: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="3D H-bond acceptor features"
    )
    feature_donor_count_3d: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="3D H-bond donor features"
    )
    feature_anion_count_3d: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="3D anion features"
    )
    feature_cation_count_3d: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="3D cation features"
    )
    feature_ring_count_3d: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="3D ring features"
    )
    feature_hydrophobe_count_3d: Series[int] | None = pa.Field(
        nullable=True, ge=0, description="3D hydrophobic features"
    )
    effective_rotor_count_3d: Series[float] | None = pa.Field(
        nullable=True, ge=0, description="Effective rotatable bonds (3D)"
    )
    conformer_rmsd_3d: Series[float] | None = pa.Field(
        nullable=True, ge=0, description="Conformer model RMSD"
    )

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
        name = "CompoundSchema"
        description = "PubChem Compound Silver layer validation"
