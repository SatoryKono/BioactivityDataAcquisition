import pandas as pd
import pandera as pa
import pytest

from bioetl.domain.schemas.chembl.document import DocumentSchema


@pytest.fixture
def valid_document_df() -> pd.DataFrame:
    schema = DocumentSchema.to_schema()
    data = {column: [None] for column in schema.columns}
    data.update(
        {
            "doc_type": ["PUBLICATION"],
            "document_chembl_id": ["CHEMBL888"],
            "doi": ["10.1000/xyz123"],
            "title": ["Study"],
            "hash_row": ["3" * 64],
            "hash_business_key": ["4" * 64],
            "index": [0],
            "database_version": ["chembl_34"],
            "extracted_at": ["2024-01-01T00:00:00+00:00"],
        }
    )
    return pd.DataFrame(data)[list(schema.columns.keys())]


def test_document_schema_accepts_valid_frame(valid_document_df: pd.DataFrame) -> None:
    validated = DocumentSchema.validate(valid_document_df)
    assert validated.equals(valid_document_df)


def test_document_schema_rejects_bad_doc_type(valid_document_df: pd.DataFrame) -> None:
    invalid = valid_document_df.copy()
    invalid["doc_type"] = ["REPORT"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        DocumentSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "doc_type" in failure_cases["column"].tolist()
    assert "REPORT" in failure_cases["failure_case"].astype(str).tolist()


def test_document_schema_rejects_bad_regex(valid_document_df: pd.DataFrame) -> None:
    invalid = valid_document_df.copy()
    invalid["document_chembl_id"] = ["bad"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        DocumentSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "document_chembl_id" in failure_cases["column"].unique()
    assert "bad" in failure_cases["failure_case"].astype(str).tolist()


def test_document_schema_rejects_null_required(valid_document_df: pd.DataFrame) -> None:
    invalid = valid_document_df.copy()
    invalid["doc_type"] = [None]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        DocumentSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert pd.isna(
        failure_cases.loc[failure_cases["column"] == "doc_type", "failure_case"].iloc[0]
    )


def test_document_schema_checks_metadata(valid_document_df: pd.DataFrame) -> None:
    invalid = valid_document_df.copy()
    invalid["hash_row"] = ["zzz"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        DocumentSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "hash_row" in failure_cases["column"].tolist()
    assert "zzz" in failure_cases["failure_case"].astype(str).tolist()


def test_document_schema_rejects_non_coercible(valid_document_df: pd.DataFrame) -> None:
    invalid = valid_document_df.copy()
    invalid["src_id"] = ["src"]

    with pytest.raises(pa.errors.SchemaErrors) as exc:
        DocumentSchema.validate(invalid, lazy=True)

    failure_cases = exc.value.failure_cases
    assert "src_id" in failure_cases["column"].unique()
    assert "src" in failure_cases["failure_case"].astype(str).tolist()
