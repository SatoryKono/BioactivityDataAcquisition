"""PubChem entity mapping and conversion utilities.

Provides entity type to data conversion mapping and record normalization.
Extracted from pubchem/client.py for better separation of concerns.
"""

from __future__ import annotations

__all__ = ["PubChemEntityMapper"]


from typing import TYPE_CHECKING, Any
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    import pubchempy as pcp


class PubChemEntityMapper:
    """Maps PubChem entities to standardized dictionary records.

    Handles conversion of pubchempy library objects to dictionaries
    suitable for Bronze layer storage.
    """

    @staticmethod
    def compound_to_dict(
        compound: pcp.Compound,
    ) -> JsonDict:  # Any: untyped API JSON record
        """Convert pubchempy Compound to dictionary.

        Uses connectivity_smiles/smiles (replaces deprecated canonical/isomeric_smiles).
        Extracts all physicochemical properties defined in PubchemMoleculeSchema.

        Note: Some properties (especially 3D) may not be available for all compounds.
        Uses getattr with default=None for safe access to optional attributes.

        Args:
            compound: PubChemPy Compound object.

        Returns:
            Dictionary with normalized compound fields including:
            - Structural identifiers (SMILES, InChI, InChI Key)
            - Nomenclature (molecular formula, IUPAC name)
            - Physical properties (molecular weight, exact mass)
            - Computed descriptors (XLogP, TPSA, complexity, charge)
            - Atom/Bond counts (heavy atoms, H-bond donors/acceptors, rotatable bonds)
            - Stereochemistry (atom/bond stereo counts)
            - 3D properties (volume, conformer count, feature counts)
        """
        molecule_id = getattr(compound, "molecule_id", None)
        if molecule_id is None or not isinstance(molecule_id, (str, int, float)):
            molecule_id = None

        cid_value = getattr(compound, "cid", None)
        if molecule_id is None and isinstance(cid_value, (str, int, float)):
            molecule_id = cid_value

        return {
            # === Primary Key ===
            "molecule_id": molecule_id,
            # Backward-compatible alias consumed by legacy client paths
            "cid": molecule_id,
            # === Structural Identifiers ===
            # Use connectivity_smiles (replaces deprecated canonical_smiles)
            "canonical_smiles": getattr(compound, "connectivity_smiles", None),
            # Use smiles (replaces deprecated isomeric_smiles)
            "isomeric_smiles": getattr(compound, "smiles", None),
            "inchi": getattr(compound, "inchi", None),
            "inchi_key": getattr(compound, "inchikey", None),
            "inchikey": getattr(compound, "inchikey", None),
            # === Nomenclature ===
            "molecular_formula": getattr(compound, "molecular_formula", None),
            "iupac_name": getattr(compound, "iupac_name", None),
            # === Physical Properties ===
            "molecular_weight": getattr(compound, "molecular_weight", None),
            "exact_mass": getattr(compound, "exact_mass", None),
            "monoisotopic_mass": getattr(compound, "monoisotopic_mass", None),
            # === Computed Descriptors ===
            "xlogp": getattr(compound, "xlogp", None),
            "tpsa": getattr(compound, "tpsa", None),
            "complexity": getattr(compound, "complexity", None),
            "charge": getattr(compound, "charge", None),
            # === Atom/Bond Counts ===
            "heavy_atom_count": getattr(compound, "heavy_atom_count", None),
            "h_bond_donor_count": getattr(compound, "h_bond_donor_count", None),
            "h_bond_acceptor_count": getattr(compound, "h_bond_acceptor_count", None),
            "rotatable_bond_count": getattr(compound, "rotatable_bond_count", None),
            # === Stereochemistry ===
            "atom_stereo_count": getattr(compound, "atom_stereo_count", None),
            "defined_atom_stereo_count": getattr(
                compound, "defined_atom_stereo_count", None
            ),
            "undefined_atom_stereo_count": getattr(
                compound, "undefined_atom_stereo_count", None
            ),
            "bond_stereo_count": getattr(compound, "bond_stereo_count", None),
            "defined_bond_stereo_count": getattr(
                compound, "defined_bond_stereo_count", None
            ),
            "undefined_bond_stereo_count": getattr(
                compound, "undefined_bond_stereo_count", None
            ),
            "isotope_atom_count": getattr(compound, "isotope_atom_count", None),
            "covalent_unit_count": getattr(compound, "covalent_unit_count", None),
            # === 3D Properties (may not be available for all compounds) ===
            "volume_3d": getattr(compound, "volume_3d", None),
            "conformer_count_3d": getattr(compound, "conformer_count_3d", None),
            "feature_acceptor_count_3d": getattr(
                compound, "feature_acceptor_count_3d", None
            ),
            "feature_donor_count_3d": getattr(compound, "feature_donor_count_3d", None),
            "feature_anion_count_3d": getattr(compound, "feature_anion_count_3d", None),
            "feature_cation_count_3d": getattr(
                compound, "feature_cation_count_3d", None
            ),
            "feature_ring_count_3d": getattr(compound, "feature_ring_count_3d", None),
            "feature_hydrophobe_count_3d": getattr(
                compound, "feature_hydrophobe_count_3d", None
            ),
            "effective_rotor_count_3d": getattr(
                compound, "effective_rotor_count_3d", None
            ),
            "conformer_rmsd_3d": getattr(compound, "conformer_rmsd_3d", None),
            # === 3D Steric Quadrupole Moments (may not be available for all compounds) ===
            "x_steric_quadrupole_3d": getattr(compound, "x_steric_quadrupole_3d", None),
            "y_steric_quadrupole_3d": getattr(compound, "y_steric_quadrupole_3d", None),
            "z_steric_quadrupole_3d": getattr(compound, "z_steric_quadrupole_3d", None),
            "feature_count_3d": getattr(compound, "feature_count_3d", None),
            # === Fingerprints (not in schema, but available) ===
            "fingerprint": getattr(compound, "fingerprint", None),
        }

    @staticmethod
    def substance_to_dict(
        substance: pcp.Substance,
    ) -> JsonDict:  # Any: untyped API JSON record
        """Convert pubchempy Substance to dictionary.

        Args:
            substance: PubChemPy Substance object.

        Returns:
            Dictionary with normalized substance fields.
        """
        return {
            "sid": substance.sid,
            "source_name": substance.source_name,
            "source_id": substance.source_id,
            "cids": substance.standardized_cids,
            "synonyms": substance.synonyms,
        }

    @staticmethod
    def assay_to_dict(
        assay: JsonDict,  # Any: untyped API JSON record
    ) -> JsonDict:  # Any: untyped API JSON record
        """Convert assay data to standardized dictionary.

        Args:
            assay: Raw assay data dictionary from PubChem.

        Returns:
            Dictionary with normalized assay fields.
        """
        return {
            "aid": assay.get("aid"),
            "name": assay.get("name"),
            "description": assay.get("description"),
            "protocol": assay.get("protocol"),
            "target": assay.get("target"),
        }
