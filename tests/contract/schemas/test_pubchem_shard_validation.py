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
    PubchemIdentitySchema.validate(dataframe_from_row(pubchem_identity_row()))


def test_pubchem_identity_shard_accepts_row_with_all_optional_checks() -> None:
    PubchemIdentitySchema.validate(pubchem_identity_valid_dataframe())


def test_pubchem_physchem_shard_accepts_row_exercising_all_checks() -> None:
    PubchemPhysChemSchema.validate(pubchem_shard_checks_dataframe(PubchemPhysChemSchema))


def test_pubchem_stereo_shard_accepts_row_exercising_all_checks() -> None:
    PubchemStereoSchema.validate(pubchem_shard_checks_dataframe(PubchemStereoSchema))


def test_pubchem_three_d_shard_accepts_row_exercising_all_checks() -> None:
    PubchemThreeDSchema.validate(pubchem_shard_checks_dataframe(PubchemThreeDSchema))


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
    PubchemMoleculeSchema.validate(dataframe_from_row(row))
