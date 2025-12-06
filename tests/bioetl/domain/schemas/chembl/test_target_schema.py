import pandas as pd
import pandera as pa
import pytest

from bioetl.domain.schemas.chembl.target import TargetSchema


@pytest.fixture
def valid_target_df() -> pd.DataFrame:
    schema = TargetSchema.to_schema()
    data = {column: [None] for column in schema.columns}
    data.update(
        {
            "target_chembl_id": ["CHEMBL222"],
            "target_type": ["SINGLE PROTEIN"],
            "uniprot_id": ["P12345"],
            "hash_row": ["1" * 64],
            "hash_business_key": ["2" * 64],
            "index": [0],
            "database_version": ["chembl_34"],
            "extracted_at": ["2024-01-01T00:00:00+00:00"],
        }
    )
    return pd.DataFrame(data)[list(schema.columns.keys())]


def test_target_schema_accepts_valid_frame(valid_target_df: pd.DataFrame) -> None:
    validated = TargetSchema.validate(valid_target_df)
    for column in [
        "target_chembl_id",
        "target_type",
        "uniprot_id",
        "hash_row",
        "hash_business_key",
        "index",
        "database_version",
        "extracted_at",
    ]:
        pd.testing.assert_series_equal(
            validated[column],
            valid_target_df[column],
            check_dtype=False,
        )


def test_target_schema_rejects_bad_chembl(valid_target_df: pd.DataFrame) -> None:
    invalid = valid_target_df.copy()
    invalid["target_chembl_id"] = ["TARGET-1"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        TargetSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "target_chembl_id" in failure_cases["column"].unique()
    assert "TARGET-1" in failure_cases["failure_case"].astype(str).tolist()


def test_target_schema_rejects_bad_uniprot(valid_target_df: pd.DataFrame) -> None:
    invalid = valid_target_df.copy()
    invalid["uniprot_id"] = ["123"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        TargetSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "uniprot_id" in failure_cases["column"].tolist()
    assert "123" in failure_cases["failure_case"].astype(str).tolist()


def test_target_schema_requires_type(valid_target_df: pd.DataFrame) -> None:
    invalid = valid_target_df.copy()
    invalid["target_type"] = [None]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        TargetSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert pd.isna(
        failure_cases.loc[
            failure_cases["column"] == "target_type", "failure_case"
        ].iloc[0]
    )


def test_target_schema_checks_metadata(valid_target_df: pd.DataFrame) -> None:
    invalid = valid_target_df.copy()
    invalid["hash_row"] = ["short"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        TargetSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "hash_row" in failure_cases["column"].tolist()
    assert "short" in failure_cases["failure_case"].astype(str).tolist()


def test_target_schema_rejects_non_coercible(valid_target_df: pd.DataFrame) -> None:
    invalid = valid_target_df.copy()
    invalid["index"] = ["bad"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        TargetSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "index" in failure_cases["column"].unique()
    assert "bad" in failure_cases["failure_case"].astype(str).tolist()
