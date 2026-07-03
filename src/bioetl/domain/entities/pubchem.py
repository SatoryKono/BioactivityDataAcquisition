# mypy: disable-error-code="misc"
"""PubChem DTO and domain entity surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.entities.base import BaseEntity
from bioetl.domain.entities.pubchem_record import PubchemMoleculeRecord


def _init_pubchem_molecule(
    self: "PubchemMolecule",
    *,
    entity_id: str,
    content_hash: str,
    run_id: str,
    run_type: str,
    ingestion_ts: datetime,
    _index: int,
    source_batch_id: str | None = None,
    _dq_warn: bool = False,
    _dq_error: bool = False,
    pubchem_cid: str | None = None,
    molecule_id: str | None = None,
    canonical_smiles: str | None = None,
    isomeric_smiles: str | None = None,
    inchi: str | None = None,
    inchi_key: str | None = None,
    standardized_canonical_smiles: str | None = None,
    standardized_isomeric_smiles: str | None = None,
    standardized_inchi: str | None = None,
    standardized_inchi_key: str | None = None,
    structure_parent_key: str | None = None,
    chemical_standardization_status: str | None = None,
    chemical_standardization_warnings: str | None = None,
    chemical_standardization_policy_version: str | None = None,
    molecular_formula: str | None = None,
    iupac_name: str | None = None,
    molecular_weight: float | str | None = None,
    exact_mass: float | None = None,
    monoisotopic_mass: float | None = None,
    xlogp: float | None = None,
    tpsa: float | None = None,
    complexity: float | None = None,
    charge: int | None = None,
    heavy_atom_count: int | None = None,
    h_bond_donor_count: int | None = None,
    h_bond_acceptor_count: int | None = None,
    rotatable_bond_count: int | None = None,
    atom_stereo_count: int | None = None,
    defined_atom_stereo_count: int | None = None,
    undefined_atom_stereo_count: int | None = None,
    bond_stereo_count: int | None = None,
    defined_bond_stereo_count: int | None = None,
    undefined_bond_stereo_count: int | None = None,
    isotope_atom_count: int | None = None,
    covalent_unit_count: int | None = None,
    volume_3d: float | None = None,
    conformer_count_3d: int | None = None,
    feature_acceptor_count_3d: int | None = None,
    feature_donor_count_3d: int | None = None,
    feature_anion_count_3d: int | None = None,
    feature_cation_count_3d: int | None = None,
    feature_ring_count_3d: int | None = None,
    feature_hydrophobe_count_3d: int | None = None,
    effective_rotor_count_3d: float | None = None,
    conformer_rmsd_3d: float | None = None,
    x_steric_quadrupole_3d: float | None = None,
    y_steric_quadrupole_3d: float | None = None,
    z_steric_quadrupole_3d: float | None = None,
    feature_count_3d: int | None = None,
    fingerprint: str | None = None,
) -> None:
    if pubchem_cid is not None and molecule_id is not None and pubchem_cid != molecule_id:
        raise ValueError(
            "PubchemMolecule received conflicting pubchem_cid and molecule_id values"
        )

    resolved_pubchem_cid = pubchem_cid if pubchem_cid is not None else molecule_id
    field_values = {
        "entity_id": entity_id,
        "content_hash": content_hash,
        "run_id": run_id,
        "run_type": run_type,
        "ingestion_ts": ingestion_ts,
        "_index": _index,
        "source_batch_id": source_batch_id,
        "_dq_warn": _dq_warn,
        "_dq_error": _dq_error,
        "pubchem_cid": resolved_pubchem_cid,
        "canonical_smiles": canonical_smiles,
        "isomeric_smiles": isomeric_smiles,
        "inchi": inchi,
        "inchi_key": inchi_key,
        "standardized_canonical_smiles": standardized_canonical_smiles,
        "standardized_isomeric_smiles": standardized_isomeric_smiles,
        "standardized_inchi": standardized_inchi,
        "standardized_inchi_key": standardized_inchi_key,
        "structure_parent_key": structure_parent_key,
        "chemical_standardization_status": chemical_standardization_status,
        "chemical_standardization_warnings": chemical_standardization_warnings,
        "chemical_standardization_policy_version": chemical_standardization_policy_version,
        "molecular_formula": molecular_formula,
        "iupac_name": iupac_name,
        "molecular_weight": molecular_weight,
        "exact_mass": exact_mass,
        "monoisotopic_mass": monoisotopic_mass,
        "xlogp": xlogp,
        "tpsa": tpsa,
        "complexity": complexity,
        "charge": charge,
        "heavy_atom_count": heavy_atom_count,
        "h_bond_donor_count": h_bond_donor_count,
        "h_bond_acceptor_count": h_bond_acceptor_count,
        "rotatable_bond_count": rotatable_bond_count,
        "atom_stereo_count": atom_stereo_count,
        "defined_atom_stereo_count": defined_atom_stereo_count,
        "undefined_atom_stereo_count": undefined_atom_stereo_count,
        "bond_stereo_count": bond_stereo_count,
        "defined_bond_stereo_count": defined_bond_stereo_count,
        "undefined_bond_stereo_count": undefined_bond_stereo_count,
        "isotope_atom_count": isotope_atom_count,
        "covalent_unit_count": covalent_unit_count,
        "volume_3d": volume_3d,
        "conformer_count_3d": conformer_count_3d,
        "feature_acceptor_count_3d": feature_acceptor_count_3d,
        "feature_donor_count_3d": feature_donor_count_3d,
        "feature_anion_count_3d": feature_anion_count_3d,
        "feature_cation_count_3d": feature_cation_count_3d,
        "feature_ring_count_3d": feature_ring_count_3d,
        "feature_hydrophobe_count_3d": feature_hydrophobe_count_3d,
        "effective_rotor_count_3d": effective_rotor_count_3d,
        "conformer_rmsd_3d": conformer_rmsd_3d,
        "x_steric_quadrupole_3d": x_steric_quadrupole_3d,
        "y_steric_quadrupole_3d": y_steric_quadrupole_3d,
        "z_steric_quadrupole_3d": z_steric_quadrupole_3d,
        "feature_count_3d": feature_count_3d,
        "fingerprint": fingerprint,
    }
    for field_name, value in field_values.items():
        object.__setattr__(self, field_name, value)
    BaseEntity.__post_init__(self)


@dataclass(frozen=True, kw_only=True, init=False)
class PubchemMolecule(BaseEntity):
    """Domain entity for a PubChem compound record."""

    pubchem_cid: str
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
    molecular_formula: str | None = None
    iupac_name: str | None = None
    molecular_weight: float | str | None = None
    exact_mass: float | None = None
    monoisotopic_mass: float | None = None
    xlogp: float | None = None
    tpsa: float | None = None
    complexity: float | None = None
    charge: int | None = None
    heavy_atom_count: int | None = None
    h_bond_donor_count: int | None = None
    h_bond_acceptor_count: int | None = None
    rotatable_bond_count: int | None = None
    atom_stereo_count: int | None = None
    defined_atom_stereo_count: int | None = None
    undefined_atom_stereo_count: int | None = None
    bond_stereo_count: int | None = None
    defined_bond_stereo_count: int | None = None
    undefined_bond_stereo_count: int | None = None
    isotope_atom_count: int | None = None
    covalent_unit_count: int | None = None
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
    fingerprint: str | None = None

    __init__ = _init_pubchem_molecule

    def _validate_invariants(self) -> None:
        if not self.pubchem_cid:
            raise ValueError("PubchemMolecule molecule_id is required")
        if not any((self.canonical_smiles, self.isomeric_smiles, self.inchi)):
            raise ValueError(
                "PubchemMolecule must have at least one structural identifier "
                "(SMILES/InChI)"
            )

    @property
    def molecule_id(self) -> str:
        return self.pubchem_cid


__all__ = ["PubchemMolecule", "PubchemMoleculeRecord"]
