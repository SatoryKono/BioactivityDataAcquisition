"""Pandera schema for PubChem Molecule entity.

Canonical name: PubchemMoleculeSchema
Deprecated alias: CompoundSchema (backward compatibility)

Aligned with RULES.md v5.0 and PubChem PUG REST API.
Source: https://pubchem.ncbi.nlm.nih.gov/rest/pug/

.. versionchanged:: 2.0.0
    CompoundSchema renamed to PubchemMoleculeSchema for Ubiquitous Language alignment.
"""

from __future__ import annotations

from typing import cast

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema


class PubchemMoleculeSchema(ETLRecordSchema):
    """PubChem Molecule validation schema for Silver layer.

    Canonical name for CompoundSchema, aligned with Ubiquitous Language.
    Represents a unique chemical structure identified by CID.

    .. versionadded:: 2.0.0
        Replaces :class:`CompoundSchema` as the canonical schema name.
    """

    # === Primary Key ===
    cid: Series[int] = pa.Field(nullable=False, description="PubChem Compound ID (PK)")

    @pa.check("cid", name="cid_positive")
    def _check_cid(cls, series: Series[int]) -> Series[bool]:
        """Validate CID is positive."""
        return cast("Series[bool]", series >= 1)

    # === Structural Identifiers ===
    canonical_smiles: Series[str] | None = pa.Field(
        nullable=True,
        description="Canonical SMILES string",
    )

    @pa.check("canonical_smiles", name="canonical_smiles_length")
    def _check_canonical_smiles(cls, series: Series[str]) -> Series[bool]:
        """Validate canonical SMILES length."""
        return cast("Series[bool]", series.isna() | (series.str.len() <= 10000))

    isomeric_smiles: Series[str] | None = pa.Field(
        nullable=True,
        description="SMILES with stereochemistry",
    )

    @pa.check("isomeric_smiles", name="isomeric_smiles_length")
    def _check_isomeric_smiles(cls, series: Series[str]) -> Series[bool]:
        """Validate isomeric SMILES length."""
        return cast("Series[bool]", series.isna() | (series.str.len() <= 10000))

    inchi: Series[str] | None = pa.Field(
        nullable=True, description="IUPAC InChI identifier"
    )

    @pa.check("inchi", name="inchi_format")
    def _check_inchi(cls, series: Series[str]) -> Series[bool]:
        """Validate InChI format."""
        return cast("Series[bool]", series.isna() | series.str.startswith("InChI="))

    inchi_key: Series[str] | None = pa.Field(
        nullable=True,
        description="InChI hash key (27 chars)",
    )

    @pa.check("inchi_key", name="inchi_key_format")
    def _check_inchi_key(cls, series: Series[str]) -> Series[bool]:
        """Validate InChI key format."""
        return cast(
            "Series[bool]",
            series.isna() | series.str.match(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$"),
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
        nullable=True, description="Average molecular weight (Da)"
    )

    @pa.check("molecular_weight", name="molecular_weight_non_negative")
    def _check_molecular_weight(cls, series: Series[float]) -> Series[bool]:
        """Validate molecular weight is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    exact_mass: Series[float] | None = pa.Field(
        nullable=True, description="Monoisotopic exact mass (Da)"
    )

    @pa.check("exact_mass", name="exact_mass_non_negative")
    def _check_exact_mass(cls, series: Series[float]) -> Series[bool]:
        """Validate exact mass is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    # === Computed Descriptors ===
    xlogp: Series[float] | None = pa.Field(
        nullable=True,
        description="Computed octanol-water partition coefficient",
    )

    @pa.check("xlogp", name="xlogp_range")
    def _check_xlogp(cls, series: Series[float]) -> Series[bool]:
        """Validate XLogP range."""
        return cast("Series[bool]", series.isna() | ((series >= -20) & (series <= 20)))

    tpsa: Series[float] | None = pa.Field(
        nullable=True, description="Topological polar surface area (Å²)"
    )

    @pa.check("tpsa", name="tpsa_non_negative")
    def _check_tpsa(cls, series: Series[float]) -> Series[bool]:
        """Validate TPSA is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    complexity: Series[float] | None = pa.Field(
        nullable=True, description="Structural complexity score"
    )

    @pa.check("complexity", name="complexity_non_negative")
    def _check_complexity(cls, series: Series[float]) -> Series[bool]:
        """Validate complexity is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    charge: Series[int] | None = pa.Field(nullable=True, description="Formal charge")

    @pa.check("charge", name="charge_range")
    def _check_charge(cls, series: Series[int]) -> Series[bool]:
        """Validate formal charge range."""
        return cast("Series[bool]", series.isna() | ((series >= -10) & (series <= 10)))

    # === Atom/Bond Counts ===
    heavy_atom_count: Series[int] | None = pa.Field(
        nullable=True, description="Non-hydrogen atom count"
    )

    @pa.check("heavy_atom_count", name="heavy_atom_count_range")
    def _check_heavy_atom_count(cls, series: Series[int]) -> Series[bool]:
        """Validate heavy atom count range."""
        return cast("Series[bool]", series.isna() | ((series >= 1) & (series <= 500)))

    h_bond_donor_count: Series[int] | None = pa.Field(
        nullable=True, description="Hydrogen bond donor count"
    )

    @pa.check("h_bond_donor_count", name="h_bond_donor_count_range")
    def _check_h_bond_donor_count(cls, series: Series[int]) -> Series[bool]:
        """Validate H-bond donor count range."""
        return cast("Series[bool]", series.isna() | ((series >= 0) & (series <= 50)))

    h_bond_acceptor_count: Series[int] | None = pa.Field(
        nullable=True, description="Hydrogen bond acceptor count"
    )

    @pa.check("h_bond_acceptor_count", name="h_bond_acceptor_count_range")
    def _check_h_bond_acceptor_count(cls, series: Series[int]) -> Series[bool]:
        """Validate H-bond acceptor count range."""
        return cast("Series[bool]", series.isna() | ((series >= 0) & (series <= 50)))

    rotatable_bond_count: Series[int] | None = pa.Field(
        nullable=True, description="Rotatable bond count"
    )

    @pa.check("rotatable_bond_count", name="rotatable_bond_count_range")
    def _check_rotatable_bond_count(cls, series: Series[int]) -> Series[bool]:
        """Validate rotatable bond count range."""
        return cast("Series[bool]", series.isna() | ((series >= 0) & (series <= 100)))

    # === Stereochemistry ===
    atom_stereo_count: Series[int] | None = pa.Field(
        nullable=True, description="Total stereocenters"
    )

    @pa.check("atom_stereo_count", name="atom_stereo_count_non_negative")
    def _check_atom_stereo_count(cls, series: Series[int]) -> Series[bool]:
        """Validate atom stereo count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    defined_atom_stereo_count: Series[int] | None = pa.Field(
        nullable=True, description="Defined stereocenters"
    )

    @pa.check(
        "defined_atom_stereo_count", name="defined_atom_stereo_count_non_negative"
    )
    def _check_defined_atom_stereo_count(cls, series: Series[int]) -> Series[bool]:
        """Validate defined atom stereo count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    undefined_atom_stereo_count: Series[int] | None = pa.Field(
        nullable=True, description="Undefined stereocenters"
    )

    @pa.check(
        "undefined_atom_stereo_count", name="undefined_atom_stereo_count_non_negative"
    )
    def _check_undefined_atom_stereo_count(cls, series: Series[int]) -> Series[bool]:
        """Validate undefined atom stereo count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    bond_stereo_count: Series[int] | None = pa.Field(
        nullable=True, description="Total E/Z bonds"
    )

    @pa.check("bond_stereo_count", name="bond_stereo_count_non_negative")
    def _check_bond_stereo_count(cls, series: Series[int]) -> Series[bool]:
        """Validate bond stereo count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    defined_bond_stereo_count: Series[int] | None = pa.Field(
        nullable=True, description="Defined E/Z bonds"
    )

    @pa.check(
        "defined_bond_stereo_count", name="defined_bond_stereo_count_non_negative"
    )
    def _check_defined_bond_stereo_count(cls, series: Series[int]) -> Series[bool]:
        """Validate defined bond stereo count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    undefined_bond_stereo_count: Series[int] | None = pa.Field(
        nullable=True, description="Undefined E/Z bonds"
    )

    @pa.check(
        "undefined_bond_stereo_count", name="undefined_bond_stereo_count_non_negative"
    )
    def _check_undefined_bond_stereo_count(cls, series: Series[int]) -> Series[bool]:
        """Validate undefined bond stereo count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    isotope_atom_count: Series[int] | None = pa.Field(
        nullable=True, description="Isotopic atom count"
    )

    @pa.check("isotope_atom_count", name="isotope_atom_count_non_negative")
    def _check_isotope_atom_count(cls, series: Series[int]) -> Series[bool]:
        """Validate isotopic atom count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    covalent_unit_count: Series[int] | None = pa.Field(
        nullable=True, description="Number of covalent units"
    )

    @pa.check("covalent_unit_count", name="covalent_unit_count_positive")
    def _check_covalent_unit_count(cls, series: Series[int]) -> Series[bool]:
        """Validate covalent unit count is positive."""
        return cast("Series[bool]", series.isna() | (series >= 1))

    # === 3D Properties ===
    volume_3d: Series[float] | None = pa.Field(
        nullable=True, description="3D molecular volume (Å³)"
    )

    @pa.check("volume_3d", name="volume_3d_non_negative")
    def _check_volume_3d(cls, series: Series[float]) -> Series[bool]:
        """Validate 3D volume is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    conformer_count_3d: Series[int] | None = pa.Field(
        nullable=True, description="Number of 3D conformers"
    )

    @pa.check("conformer_count_3d", name="conformer_count_3d_non_negative")
    def _check_conformer_count_3d(cls, series: Series[int]) -> Series[bool]:
        """Validate 3D conformer count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    feature_acceptor_count_3d: Series[int] | None = pa.Field(
        nullable=True, description="3D H-bond acceptor features"
    )

    @pa.check(
        "feature_acceptor_count_3d", name="feature_acceptor_count_3d_non_negative"
    )
    def _check_feature_acceptor_count_3d(cls, series: Series[int]) -> Series[bool]:
        """Validate 3D H-bond acceptor count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    feature_donor_count_3d: Series[int] | None = pa.Field(
        nullable=True, description="3D H-bond donor features"
    )

    @pa.check("feature_donor_count_3d", name="feature_donor_count_3d_non_negative")
    def _check_feature_donor_count_3d(cls, series: Series[int]) -> Series[bool]:
        """Validate 3D H-bond donor count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    feature_anion_count_3d: Series[int] | None = pa.Field(
        nullable=True, description="3D anion features"
    )

    @pa.check("feature_anion_count_3d", name="feature_anion_count_3d_non_negative")
    def _check_feature_anion_count_3d(cls, series: Series[int]) -> Series[bool]:
        """Validate 3D anion count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    feature_cation_count_3d: Series[int] | None = pa.Field(
        nullable=True, description="3D cation features"
    )

    @pa.check("feature_cation_count_3d", name="feature_cation_count_3d_non_negative")
    def _check_feature_cation_count_3d(cls, series: Series[int]) -> Series[bool]:
        """Validate 3D cation count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    feature_ring_count_3d: Series[int] | None = pa.Field(
        nullable=True, description="3D ring features"
    )

    @pa.check("feature_ring_count_3d", name="feature_ring_count_3d_non_negative")
    def _check_feature_ring_count_3d(cls, series: Series[int]) -> Series[bool]:
        """Validate 3D ring count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    feature_hydrophobe_count_3d: Series[int] | None = pa.Field(
        nullable=True, description="3D hydrophobic features"
    )

    @pa.check(
        "feature_hydrophobe_count_3d", name="feature_hydrophobe_count_3d_non_negative"
    )
    def _check_feature_hydrophobe_count_3d(cls, series: Series[int]) -> Series[bool]:
        """Validate 3D hydrophobic count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    effective_rotor_count_3d: Series[float] | None = pa.Field(
        nullable=True, description="Effective rotatable bonds (3D)"
    )

    @pa.check("effective_rotor_count_3d", name="effective_rotor_count_3d_non_negative")
    def _check_effective_rotor_count_3d(cls, series: Series[float]) -> Series[bool]:
        """Validate 3D effective rotor count is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    conformer_rmsd_3d: Series[float] | None = pa.Field(
        nullable=True, description="Conformer model RMSD"
    )

    @pa.check("conformer_rmsd_3d", name="conformer_rmsd_3d_non_negative")
    def _check_conformer_rmsd_3d(cls, series: Series[float]) -> Series[bool]:
        """Validate 3D conformer RMSD is non-negative."""
        return cast("Series[bool]", series.isna() | (series >= 0))

    class Config:
        """Pandera configuration."""

        strict = True
        ordered = True
        coerce = True
        name = "PubchemMoleculeSchema"
        description = "PubChem Molecule Silver layer validation"


# === Deprecated Alias (backward compatibility) ===

# CompoundSchema is a deprecated alias for PubchemMoleculeSchema.
# Use PubchemMoleculeSchema in new code for Ubiquitous Language alignment.
#
# .. deprecated:: 2.0.0
#     Use :class:`PubchemMoleculeSchema` instead.
CompoundSchema = PubchemMoleculeSchema
