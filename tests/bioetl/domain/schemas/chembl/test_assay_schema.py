import pandas as pd
import pandera as pa
import pytest

from bioetl.domain.schemas.chembl.assay import AssaySchema


@pytest.fixture
def valid_assay_df() -> pd.DataFrame:
    schema = AssaySchema.to_schema()
    data = {column: [None] for column in schema.columns}
    data.update(
        {
            "assay_chembl_id": ["CHEMBL777"],
            "assay_type": ["B"],
            "assay_category": ["screening"],
            "confidence_score": [5],
            "hash_row": ["c" * 64],
            "hash_business_key": ["d" * 64],
            "index": [0],
            "database_version": ["chembl_34"],
            "extracted_at": ["2024-01-01T00:00:00+00:00"],
        }
    )
    return pd.DataFrame(data)[list(schema.columns.keys())]


def test_assay_schema_accepts_valid_frame(valid_assay_df: pd.DataFrame) -> None:
    validated = AssaySchema.validate(valid_assay_df)
    pd.testing.assert_frame_equal(
        validated,
        valid_assay_df,
        check_dtype=False,
    )


def test_assay_schema_rejects_bad_enum(valid_assay_df: pd.DataFrame) -> None:
    invalid = valid_assay_df.copy()
    invalid["assay_type"] = ["X"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        AssaySchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "assay_type" in failure_cases["column"].tolist()
    assert "X" in failure_cases["failure_case"].astype(str).tolist()


def test_assay_schema_rejects_bad_regex(valid_assay_df: pd.DataFrame) -> None:
    invalid = valid_assay_df.copy()
    invalid["assay_chembl_id"] = ["chembl-1"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        AssaySchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "assay_chembl_id" in failure_cases["column"].unique()
    assert "chembl-1" in failure_cases["failure_case"].astype(str).tolist()


def test_assay_schema_rejects_out_of_range(valid_assay_df: pd.DataFrame) -> None:
    invalid = valid_assay_df.copy()
    invalid["confidence_score"] = [15]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        AssaySchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert (
        failure_cases.loc[
            failure_cases["column"] == "confidence_score", "failure_case"
        ].iloc[0]
        == 15
    )


def test_assay_schema_requires_hash(valid_assay_df: pd.DataFrame) -> None:
    invalid = valid_assay_df.copy()
    invalid["hash_row"] = ["abc"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        AssaySchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "hash_row" in failure_cases["column"].tolist()
    assert "abc" in failure_cases["failure_case"].astype(str).tolist()


def test_assay_schema_rejects_null_required(valid_assay_df: pd.DataFrame) -> None:
    invalid = valid_assay_df.copy()
    invalid["assay_chembl_id"] = [None]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        AssaySchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert pd.isna(
        failure_cases.loc[
            failure_cases["column"] == "assay_chembl_id", "failure_case"
        ].iloc[0]
    )
