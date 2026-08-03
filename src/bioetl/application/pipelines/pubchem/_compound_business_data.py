"""Helpers for assembling PubChem compound business payloads."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.behavior import standardize_chemical_structure
from bioetl.domain.transformations import safe_float, safe_int
from bioetl.domain.validation import validate_molecular_weight, validate_non_negative
from bioetl.domain.value_objects import InChIKey

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.types import BronzeRecord


def build_compound_business_data(
    record: BronzeRecord,
    *,
    validate_inchi_key: Callable[[type[InChIKey], object], object],
    serialize_json_list: Callable[[list[object]], str | None],
) -> tuple[object, dict[str, object]] | None:
    """Build the normalized PubChem compound business payload."""
    cid = _resolve_compound_identifier(record)
    if cid is None:
        return None

    computed_descriptors = _extract_computed_descriptors(record)
    stereochemistry = _extract_stereochemistry(record)
    charge = safe_int(record.get("charge"))
    business_data: dict[str, object] = {
        "molecule_id": str(cid),
        "canonical_smiles": record.get("canonical_smiles"),
        "isomeric_smiles": record.get("isomeric_smiles"),
        "inchi": record.get("inchi"),
        "inchi_key": validate_inchi_key(
            InChIKey,
            record.get("inchikey") or record.get("inchi_key"),
        ),
        "molecular_formula": record.get("molecular_formula"),
        "iupac_name": record.get("iupac_name"),
        "molecular_weight": validate_molecular_weight(record.get("molecular_weight")),
        "exact_mass": validate_non_negative(record.get("exact_mass")),
        "monoisotopic_mass": validate_non_negative(record.get("monoisotopic_mass")),
        **computed_descriptors,
        **_extract_atom_bond_counts(record),
        **stereochemistry,
        **_extract_3d_properties(record),
        **_extract_chemical_standardization(
            record,
            covalent_unit_count=stereochemistry["covalent_unit_count"],
            charge=charge,
            serialize_json_list=serialize_json_list,
        ),
    }
    return cid, business_data


def _resolve_compound_identifier(record: BronzeRecord) -> object | None:
    """Return the canonical PubChem compound identifier from Bronze payload."""
    cid: object | None = record.get("cid")
    if cid not in (None, ""):
        return cid
    molecule_id: object | None = record.get("molecule_id")
    return molecule_id if molecule_id not in (None, "") else None


def _extract_computed_descriptors(
    record: BronzeRecord,
) -> dict[str, float | int | None]:
    """Extract and validate computed molecular descriptors."""
    return {
        "xlogp": safe_float(record.get("xlogp")),
        "tpsa": validate_non_negative(record.get("tpsa")),
        "complexity": validate_non_negative(record.get("complexity")),
        "charge": safe_int(record.get("charge")),
    }


def _extract_atom_bond_counts(record: BronzeRecord) -> dict[str, int | None]:
    """Extract and validate atom/bond count properties."""
    return {
        "heavy_atom_count": safe_int(record.get("heavy_atom_count")),
        "h_bond_donor_count": safe_int(record.get("h_bond_donor_count")),
        "h_bond_acceptor_count": safe_int(record.get("h_bond_acceptor_count")),
        "rotatable_bond_count": safe_int(record.get("rotatable_bond_count")),
    }


def _extract_stereochemistry(record: BronzeRecord) -> dict[str, int | None]:
    """Extract and validate stereochemistry counts."""
    return {
        "atom_stereo_count": safe_int(record.get("atom_stereo_count")),
        "defined_atom_stereo_count": safe_int(record.get("defined_atom_stereo_count")),
        "undefined_atom_stereo_count": safe_int(
            record.get("undefined_atom_stereo_count")
        ),
        "bond_stereo_count": safe_int(record.get("bond_stereo_count")),
        "defined_bond_stereo_count": safe_int(record.get("defined_bond_stereo_count")),
        "undefined_bond_stereo_count": safe_int(
            record.get("undefined_bond_stereo_count")
        ),
        "isotope_atom_count": safe_int(record.get("isotope_atom_count")),
        "covalent_unit_count": safe_int(record.get("covalent_unit_count")),
    }


def _extract_3d_properties(record: BronzeRecord) -> dict[str, float | int | None]:
    """Extract and validate 3D molecular properties."""
    return {
        "volume_3d": validate_non_negative(record.get("volume_3d")),
        "conformer_count_3d": safe_int(record.get("conformer_count_3d")),
        "feature_acceptor_count_3d": safe_int(record.get("feature_acceptor_count_3d")),
        "feature_donor_count_3d": safe_int(record.get("feature_donor_count_3d")),
        "feature_anion_count_3d": safe_int(record.get("feature_anion_count_3d")),
        "feature_cation_count_3d": safe_int(record.get("feature_cation_count_3d")),
        "feature_ring_count_3d": safe_int(record.get("feature_ring_count_3d")),
        "feature_hydrophobe_count_3d": safe_int(
            record.get("feature_hydrophobe_count_3d")
        ),
        "effective_rotor_count_3d": validate_non_negative(
            record.get("effective_rotor_count_3d")
        ),
        "conformer_rmsd_3d": validate_non_negative(record.get("conformer_rmsd_3d")),
        "x_steric_quadrupole_3d": safe_float(record.get("x_steric_quadrupole_3d")),
        "y_steric_quadrupole_3d": safe_float(record.get("y_steric_quadrupole_3d")),
        "z_steric_quadrupole_3d": safe_float(record.get("z_steric_quadrupole_3d")),
        "feature_count_3d": safe_int(record.get("feature_count_3d")),
    }


def _extract_chemical_standardization(
    record: BronzeRecord,
    *,
    covalent_unit_count: int | None,
    charge: int | None,
    serialize_json_list: Callable[[list[object]], str | None],
) -> dict[str, str | None]:
    """Apply the governed PubChem chemical standardization policy."""
    result = standardize_chemical_structure(
        canonical_smiles=record.get("canonical_smiles"),
        isomeric_smiles=record.get("isomeric_smiles"),
        inchi=record.get("inchi"),
        inchi_key=record.get("inchikey") or record.get("inchi_key"),
        covalent_unit_count=covalent_unit_count,
        charge=charge,
    )
    return {
        "standardized_canonical_smiles": result.standardized_canonical_smiles,
        "standardized_isomeric_smiles": result.standardized_isomeric_smiles,
        "standardized_inchi": result.standardized_inchi,
        "standardized_inchi_key": result.standardized_inchi_key,
        "structure_parent_key": result.structure_parent_key,
        "chemical_standardization_status": result.chemical_standardization_status,
        "chemical_standardization_warnings": serialize_json_list(
            list(result.chemical_standardization_warnings)
        ),
        "chemical_standardization_policy_version": (
            result.chemical_standardization_policy_version
        ),
    }
