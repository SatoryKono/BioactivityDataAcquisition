"""PubChem entity mapping and conversion utilities.

Provides entity type to data conversion mapping and record normalization.
Extracted from pubchem/client.py for better separation of concerns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pubchempy as pcp


class PubChemEntityMapper:
    """Maps PubChem entities to standardized dictionary records.

    Handles conversion of pubchempy library objects to dictionaries
    suitable for Bronze layer storage.
    """

    @staticmethod
    def compound_to_dict(compound: pcp.Compound) -> dict[str, Any]:
        """Convert pubchempy Compound to dictionary.

        Uses connectivity_smiles/smiles (replaces deprecated canonical/isomeric_smiles).

        Args:
            compound: PubChemPy Compound object.

        Returns:
            Dictionary with normalized compound fields.
        """
        return {
            "cid": compound.cid,
            "molecular_formula": compound.molecular_formula,
            "molecular_weight": compound.molecular_weight,
            # Use connectivity_smiles (replaces deprecated canonical_smiles)
            "canonical_smiles": compound.connectivity_smiles,
            # Use smiles (replaces deprecated isomeric_smiles)
            "isomeric_smiles": compound.smiles,
            "inchi": compound.inchi,
            "inchikey": compound.inchikey,
            "iupac_name": compound.iupac_name,
            "charge": compound.charge,
            "complexity": compound.complexity,
            "h_bond_acceptor_count": compound.h_bond_acceptor_count,
            "h_bond_donor_count": compound.h_bond_donor_count,
            "rotatable_bond_count": compound.rotatable_bond_count,
            "fingerprint": compound.fingerprint,
        }

    @staticmethod
    def substance_to_dict(substance: pcp.Substance) -> dict[str, Any]:
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
    def assay_to_dict(assay: dict[str, Any]) -> dict[str, Any]:
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
