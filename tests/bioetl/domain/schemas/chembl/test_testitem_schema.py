import pandas as pd
import pandera as pa
import pytest

from bioetl.domain.schemas.chembl.testitem import TestitemSchema


@pytest.fixture
def valid_testitem_df() -> pd.DataFrame:
    schema = TestitemSchema.to_schema()
    data = {column: [None] for column in schema.columns}
    data.update(
        {
            "molecule_chembl_id": ["CHEMBL555"],
            "molecule_type": ["Small molecule"],
            "max_phase": [2],
            "pubchem_cid": ["123456"],
            "hash_row": ["9" * 64],
            "hash_business_key": ["8" * 64],
            "index": [0],
            "database_version": ["chembl_34"],
            "extracted_at": ["2024-01-01T00:00:00+00:00"],
        }
    )
    return pd.DataFrame(data)[list(schema.columns.keys())]


def test_testitem_schema_accepts_valid_frame(valid_testitem_df: pd.DataFrame) -> None:
    validated = TestitemSchema.validate(valid_testitem_df)
    pd.testing.assert_frame_equal(
        validated,
        valid_testitem_df,
        check_dtype=False,
    )


def test_testitem_schema_rejects_bad_chembl(valid_testitem_df: pd.DataFrame) -> None:
    invalid = valid_testitem_df.copy()
    invalid["molecule_chembl_id"] = ["chembl-555"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        TestitemSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "molecule_chembl_id" in failure_cases["column"].unique()
    assert "chembl-555" in failure_cases["failure_case"].astype(str).tolist()


def test_testitem_schema_rejects_invalid_pubchem(valid_testitem_df: pd.DataFrame) -> None:
    invalid = valid_testitem_df.copy()
    invalid["pubchem_cid"] = ["CID-1"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        TestitemSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "pubchem_cid" in failure_cases["column"].tolist()
    assert "CID-1" in failure_cases["failure_case"].astype(str).tolist()


def test_testitem_schema_rejects_out_of_range(valid_testitem_df: pd.DataFrame) -> None:
    invalid = valid_testitem_df.copy()
    invalid["max_phase"] = [-1]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        TestitemSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert failure_cases.loc[failure_cases["column"] == "max_phase", "failure_case"].iloc[0] == -1


def test_testitem_schema_checks_metadata(valid_testitem_df: pd.DataFrame) -> None:
    invalid = valid_testitem_df.copy()
    invalid["hash_row"] = ["short"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        TestitemSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "hash_row" in failure_cases["column"].unique()
    assert "short" in failure_cases["failure_case"].astype(str).tolist()


def test_testitem_schema_rejects_non_coercible(valid_testitem_df: pd.DataFrame) -> None:
    invalid = valid_testitem_df.copy()
    invalid["index"] = ["idx"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        TestitemSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "index" in failure_cases["column"].unique()
    assert "idx" in failure_cases["failure_case"].astype(str).tolist()
