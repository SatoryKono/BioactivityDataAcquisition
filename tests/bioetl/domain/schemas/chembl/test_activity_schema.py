import pandas as pd
import pandera as pa
import pytest

from bioetl.domain.schemas.chembl.activity import ActivitySchema


@pytest.fixture
def valid_activity_df() -> pd.DataFrame:
    schema = ActivitySchema.to_schema()
    data = {column: [None] for column in schema.columns}
    data.update(
        {
            "action_type": ["agonist"],
            "activity_comment": ["ok"],
            "activity_id": [1],
            "assay_chembl_id": ["CHEMBL123"],
            "assay_type": ["B"],
            "document_chembl_id": ["CHEMBL999"],
            "molecule_chembl_id": ["CHEMBL321"],
            "standard_flag": [True],
            "hash_row": ["a" * 64],
            "hash_business_key": ["b" * 64],
            "index": [0],
            "database_version": ["chembl_34"],
            "extracted_at": ["2024-01-01T00:00:00+00:00"],
        }
    )
    return pd.DataFrame(data)[list(schema.columns.keys())]


def test_activity_schema_accepts_valid_frame(valid_activity_df: pd.DataFrame) -> None:
    validated = ActivitySchema.validate(valid_activity_df)
    for column in [
        "action_type",
        "activity_comment",
        "activity_id",
        "assay_chembl_id",
        "assay_type",
        "document_chembl_id",
        "molecule_chembl_id",
        "standard_flag",
        "hash_row",
        "hash_business_key",
        "index",
        "database_version",
        "extracted_at",
    ]:
        pd.testing.assert_series_equal(
            validated[column],
            valid_activity_df[column],
            check_dtype=False,
        )


def test_activity_schema_rejects_bad_chembl(valid_activity_df: pd.DataFrame) -> None:
    invalid = valid_activity_df.copy()
    invalid["assay_chembl_id"] = ["BAD"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        ActivitySchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "assay_chembl_id" in failure_cases["column"].unique()
    assert "BAD" in failure_cases["failure_case"].astype(str).tolist()


def test_activity_schema_rejects_out_of_range_value(valid_activity_df: pd.DataFrame) -> None:
    invalid = valid_activity_df.copy()
    invalid["pchembl_value"] = [16.5]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        ActivitySchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert failure_cases.loc[failure_cases["column"] == "pchembl_value", "failure_case"].iloc[0] == 16.5


def test_activity_schema_blocks_null_required(valid_activity_df: pd.DataFrame) -> None:
    invalid = valid_activity_df.copy()
    invalid["activity_id"] = [None]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        ActivitySchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert set(failure_cases["column"]) == {"activity_id"}


def test_activity_schema_validates_categories(valid_activity_df: pd.DataFrame) -> None:
    invalid = valid_activity_df.copy()
    invalid["assay_type"] = ["X"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        ActivitySchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "assay_type" in failure_cases["column"].tolist()
    assert "X" in failure_cases["failure_case"].astype(str).tolist()


def test_activity_schema_checks_metadata_hash(valid_activity_df: pd.DataFrame) -> None:
    invalid = valid_activity_df.copy()
    invalid["hash_row"] = ["short"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        ActivitySchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "hash_row" in failure_cases["column"].unique()
    assert "short" in failure_cases["failure_case"].astype(str).tolist()


def test_activity_schema_rejects_non_coercible(valid_activity_df: pd.DataFrame) -> None:
    invalid = valid_activity_df.copy()
    invalid["activity_id"] = ["abc"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        ActivitySchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "activity_id" in failure_cases["column"].unique()
    assert "abc" in failure_cases["failure_case"].astype(str).tolist()
