"""Contract validation for PubChem schema shards."""

from __future__ import annotations

import pandas as pd
import pandera as pa
import pytest

from bioetl.domain.schemas.pubchem._identifiers import PubchemIdentitySchema
from bioetl.domain.schemas.pubchem._physchem import PubchemPhysChemSchema
from bioetl.domain.schemas.pubchem._stereo import PubchemStereoSchema
from bioetl.domain.schemas.pubchem._three_d import PubchemThreeDSchema
from bioetl.domain.schemas.pubchem.compound import PubchemMoleculeSchema
from tests.contract.schemas._schema_row_helpers import (
    dataframe_from_row,
    pubchem_identity_row,
    pubchem_identity_valid_dataframe,
    pubchem_shard_checks_dataframe,
)

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


def test_pubchem_identity_shard_accepts_minimal_valid_row() -> None:
    validated = PubchemIdentitySchema.validate(
        dataframe_from_row(pubchem_identity_row())
    )
    assert validated["molecule_id"].iloc[0] == "2244"


def test_pubchem_identity_shard_accepts_row_with_all_optional_checks() -> None:
    validated = PubchemIdentitySchema.validate(pubchem_identity_valid_dataframe())
    assert validated["inchi"].iloc[0].startswith("InChI=")


def test_pubchem_physchem_shard_accepts_row_exercising_all_checks() -> None:
    validated = PubchemPhysChemSchema.validate(
        pubchem_shard_checks_dataframe(PubchemPhysChemSchema)
    )
    assert float(validated["molecular_weight"].iloc[0]) > 0


def test_pubchem_stereo_shard_accepts_row_exercising_all_checks() -> None:
    validated = PubchemStereoSchema.validate(
        pubchem_shard_checks_dataframe(PubchemStereoSchema)
    )
    assert int(validated["atom_stereo_count"].iloc[0]) >= 0


def test_pubchem_three_d_shard_accepts_row_exercising_all_checks() -> None:
    validated = PubchemThreeDSchema.validate(
        pubchem_shard_checks_dataframe(PubchemThreeDSchema)
    )
    assert float(validated["volume_3d"].iloc[0]) >= 0


@pytest.mark.parametrize("molecule_id", ["0", "-1", "abc", ""])
def test_pubchem_identity_shard_rejects_invalid_molecule_id(molecule_id: str) -> None:
    with pytest.raises(pa.errors.SchemaError):
        PubchemIdentitySchema.validate(
            dataframe_from_row(pubchem_identity_row(molecule_id=molecule_id))
        )


def test_pubchem_identity_shard_rejects_invalid_inchi_prefix() -> None:
    with pytest.raises(pa.errors.SchemaError):
        PubchemIdentitySchema.validate(
            dataframe_from_row(pubchem_identity_row(inchi="not-inchi"))
        )


def test_pubchem_physchem_shard_rejects_negative_molecular_weight() -> None:
    df = pd.DataFrame([{"molecular_weight": -1.0}])
    with pytest.raises(pa.errors.SchemaError):
        PubchemPhysChemSchema.validate(df)


def test_pubchem_physchem_shard_rejects_xlogp_out_of_range() -> None:
    df = pd.DataFrame([{"xlogp": 25.0}])
    with pytest.raises(pa.errors.SchemaError):
        PubchemPhysChemSchema.validate(df)


def test_pubchem_stereo_shard_rejects_negative_atom_stereo_count() -> None:
    df = pd.DataFrame([{"atom_stereo_count": -1}])
    with pytest.raises(pa.errors.SchemaError):
        PubchemStereoSchema.validate(df)


def test_pubchem_three_d_shard_rejects_negative_volume() -> None:
    df = pd.DataFrame([{"volume_3d": -0.1}])
    with pytest.raises(pa.errors.SchemaError):
        PubchemThreeDSchema.validate(df)


def test_pubchem_molecule_schema_accepts_composed_minimal_row() -> None:
    row = pubchem_identity_row(
        molecular_weight=180.16,
        xlogp=1.2,
        atom_stereo_count=0,
        volume_3d=100.0,
    )
    validated = PubchemMoleculeSchema.validate(dataframe_from_row(row))
    assert validated["molecule_id"].iloc[0] == "2244"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("exact_mass", -0.1),
        ("monoisotopic_mass", -0.1),
        ("tpsa", -0.1),
        ("complexity", -0.1),
        ("charge", 11),
        ("heavy_atom_count", 0),
        ("h_bond_donor_count", 51),
        ("h_bond_acceptor_count", -1),
        ("rotatable_bond_count", 101),
    ],
)
def test_pubchem_physchem_shard_rejects_additional_invalid_ranges(
    field: str,
    value: float | int,
) -> None:
    df = pubchem_shard_checks_dataframe(PubchemPhysChemSchema)
    df.loc[0, field] = value
    with pytest.raises(pa.errors.SchemaError):
        PubchemPhysChemSchema.validate(df)


@pytest.mark.parametrize(
    "field",
    [
        "conformer_count_3d",
        "feature_acceptor_count_3d",
        "feature_donor_count_3d",
        "feature_anion_count_3d",
        "feature_cation_count_3d",
        "feature_ring_count_3d",
        "feature_hydrophobe_count_3d",
        "effective_rotor_count_3d",
        "conformer_rmsd_3d",
        "feature_count_3d",
    ],
)
def test_pubchem_three_d_shard_rejects_negative_counts(field: str) -> None:
    df = pubchem_shard_checks_dataframe(PubchemThreeDSchema)
    df.loc[0, field] = -0.1
    with pytest.raises(pa.errors.SchemaError):
        PubchemThreeDSchema.validate(df)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("defined_atom_stereo_count", -1),
        ("undefined_atom_stereo_count", -1),
        ("bond_stereo_count", -1),
        ("defined_bond_stereo_count", -1),
        ("undefined_bond_stereo_count", -1),
        ("isotope_atom_count", -1),
        ("covalent_unit_count", 0),
    ],
)
def test_pubchem_stereo_shard_rejects_invalid_stereo_counts(
    field: str,
    value: int,
) -> None:
    df = pubchem_shard_checks_dataframe(PubchemStereoSchema)
    df.loc[0, field] = value
    with pytest.raises(pa.errors.SchemaError):
        PubchemStereoSchema.validate(df)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("canonical_smiles", "C" * 10001),
        ("isomeric_smiles", "C" * 10001),
        ("inchi_key", "BAD-INCHI-KEY"),
        ("standardized_inchi", "bad"),
        ("standardized_inchi_key", "BAD-INCHI-KEY"),
        ("structure_parent_key", "x" * 10051),
        ("chemical_standardization_status", "unknown"),
        ("chemical_standardization_policy_version", "policy-v0"),
    ],
)
def test_pubchem_identity_shard_rejects_additional_invalid_identifier_fields(
    field: str,
    value: str,
) -> None:
    df = pubchem_identity_valid_dataframe()
    df.loc[0, field] = value
    with pytest.raises(pa.errors.SchemaError):
        PubchemIdentitySchema.validate(df)
