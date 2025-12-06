import pandas as pd
import pandera as pa
import pytest

from bioetl.domain.schemas.chembl.molecule import MoleculeSchema


@pytest.fixture
def valid_molecule_df() -> pd.DataFrame:
    schema = MoleculeSchema.to_schema()
    data = {column: [None] for column in schema.columns}
    data.update(
        {
            "molecule_chembl_id": ["CHEMBL42"],
            "max_phase": [3],
            "oral": [True],
            "hash_row": ["e" * 64],
            "hash_business_key": ["f" * 64],
            "index": [0],
            "database_version": ["chembl_34"],
            "extracted_at": ["2024-01-01T00:00:00+00:00"],
        }
    )
    return pd.DataFrame(data)[list(schema.columns.keys())]


def test_molecule_schema_accepts_valid_frame(valid_molecule_df: pd.DataFrame) -> None:
    validated = MoleculeSchema.validate(valid_molecule_df)
    for column in [
        "molecule_chembl_id",
        "max_phase",
        "oral",
        "hash_row",
        "hash_business_key",
        "index",
        "database_version",
        "extracted_at",
    ]:
        pd.testing.assert_series_equal(
            validated[column],
            valid_molecule_df[column],
            check_dtype=False,
        )


def test_molecule_schema_rejects_bad_chembl(valid_molecule_df: pd.DataFrame) -> None:
    invalid = valid_molecule_df.copy()
    invalid["molecule_chembl_id"] = ["chembl42"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        MoleculeSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "molecule_chembl_id" in failure_cases["column"].unique()
    assert "chembl42" in failure_cases["failure_case"].astype(str).tolist()


def test_molecule_schema_rejects_out_of_range(valid_molecule_df: pd.DataFrame) -> None:
    invalid = valid_molecule_df.copy()
    invalid["max_phase"] = [10]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        MoleculeSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert failure_cases.loc[failure_cases["column"] == "max_phase", "failure_case"].iloc[0] == 10


def test_molecule_schema_rejects_non_nullable(valid_molecule_df: pd.DataFrame) -> None:
    invalid = valid_molecule_df.copy()
    invalid["molecule_chembl_id"] = [None]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        MoleculeSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert pd.isna(
        failure_cases.loc[
            failure_cases["column"] == "molecule_chembl_id", "failure_case"
        ].iloc[0]
    )


def test_molecule_schema_checks_metadata(valid_molecule_df: pd.DataFrame) -> None:
    invalid = valid_molecule_df.copy()
    invalid["index"] = [-1]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        MoleculeSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "index" in failure_cases["column"].tolist()
    assert -1 in failure_cases["failure_case"].tolist()


def test_molecule_schema_rejects_non_coercible(valid_molecule_df: pd.DataFrame) -> None:
    invalid = valid_molecule_df.copy()
    invalid["max_phase"] = ["definitely"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        MoleculeSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "max_phase" in failure_cases["column"].unique()
    assert "definitely" in failure_cases["failure_case"].astype(str).tolist()
