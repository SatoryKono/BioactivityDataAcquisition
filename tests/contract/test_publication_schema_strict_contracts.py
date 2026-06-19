"""Contract tests for publication Silver/Gold schema strict constraints."""

from __future__ import annotations

import pandas as pd
import pandera as pa
import pytest

from bioetl.domain.contracts.gold.publications_pubmed import PubMedPublicationGoldSchema
from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


def test_pubmed_silver_schema_accepts_minimal_fixture(
    minimal_pubmed_publication_df: pd.DataFrame,
) -> None:
    validated = PubMedPublicationSchema.validate(minimal_pubmed_publication_df)
    assert validated["pmid"].iloc[0] == "12345678"


def test_pubmed_silver_schema_rejects_invalid_pmid(
    minimal_pubmed_publication_df: pd.DataFrame,
) -> None:
    df = minimal_pubmed_publication_df.copy()
    df.loc[0, "pmid"] = "0"
    with pytest.raises(pa.errors.SchemaError):
        PubMedPublicationSchema.validate(df)


def _minimal_pubmed_gold_df(
    minimal_pubmed_publication_df: pd.DataFrame,
) -> pd.DataFrame:
    silver = minimal_pubmed_publication_df.iloc[0]
    row: dict[str, object] = {}
    for column_name, column in PubMedPublicationGoldSchema.to_schema().columns.items():
        if column_name in silver.index:
            row[column_name] = silver[column_name]
        elif not column.nullable:
            if column.dtype == "bool":
                row[column_name] = False
            elif column.dtype == "int64":
                row[column_name] = int(0)
            elif column.dtype == "float64":
                row[column_name] = 0.0
            else:
                row[column_name] = f"value-{column_name}"
        else:
            row[column_name] = None
    row.update(
        {
            "entity_id": "pubmed:12345678",
            "content_hash": "a" * 64,
            "_index": int(0),
            "_dq_warn": False,
            "_dq_error": False,
            "_source": "pubmed",
            "_lookup_method": "direct",
        }
    )
    frame = pd.DataFrame([row])
    frame["_index"] = frame["_index"].astype("int64")
    frame["_dq_warn"] = frame["_dq_warn"].astype("bool")
    frame["_dq_error"] = frame["_dq_error"].astype("bool")
    return frame


def test_pubmed_gold_strict_minimal_row_validates(
    minimal_pubmed_publication_df: pd.DataFrame,
) -> None:
    validated = PubMedPublicationGoldSchema.validate(
        _minimal_pubmed_gold_df(minimal_pubmed_publication_df)
    )
    assert validated["pmid"].iloc[0] == "12345678"


def test_pubmed_gold_strict_rejects_extra_column(
    minimal_pubmed_publication_df: pd.DataFrame,
) -> None:
    gold_df = _minimal_pubmed_gold_df(minimal_pubmed_publication_df)
    gold_df["__unexpected__"] = "x"
    with pytest.raises((pa.errors.SchemaError, pa.errors.SchemaErrors)):
        PubMedPublicationGoldSchema.validate(gold_df)
