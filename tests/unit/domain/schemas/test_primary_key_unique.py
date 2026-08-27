# pyright: reportArgumentType=false
"""Entity primary keys declare unique=True (#9635)."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
import pytest

from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.publication_term import PublicationTermSchema
from bioetl.domain.schemas.chembl.target_protein_classification import (
    TargetProteinClassificationSchema,
)


@pytest.mark.unit
def test_activity_id_column_is_unique() -> None:
    column = ActivitySchema.to_schema().columns["activity_id"]
    assert column.unique is True


@pytest.mark.unit
def test_unique_constraint_rejects_duplicate_pk_values() -> None:
    schema = pa.DataFrameSchema({"activity_id": pa.Column(str, unique=True)})
    df = pd.DataFrame({"activity_id": ["CHEMBL1", "CHEMBL1"]})
    with pytest.raises(pa.errors.SchemaError):
        schema.validate(df)


@pytest.mark.unit
def test_publication_term_composite_unique_is_immutable() -> None:
    unique = PublicationTermSchema.to_schema().unique
    assert tuple(unique) == ("publication_id", "term_type", "term")


def _tpc_row(*, entity_id: str, index: int) -> dict[str, object]:
    return {
        "entity_id": entity_id,
        "content_hash": "a" * 64,
        "_run_id": "run-1",
        "_run_type": "incremental",
        "_ingestion_ts": "2026-08-27T00:00:00Z",
        "_index": index,
        "_dq_warn": False,
        "_dq_error": False,
        "target_id": "CHEMBL1",
        "classification_status": "resolved",
    }


@pytest.mark.unit
def test_target_protein_classification_entity_id_unique() -> None:
    unique = TargetProteinClassificationSchema.to_schema().unique
    assert tuple(unique) == ("entity_id",)


@pytest.mark.unit
def test_target_protein_classification_rejects_duplicate_entity_id() -> None:
    schema = TargetProteinClassificationSchema.to_schema()
    df = pd.DataFrame(
        [
            _tpc_row(entity_id="tpc-dup", index=0),
            _tpc_row(entity_id="tpc-dup", index=1),
        ]
    )
    with pytest.raises(pa.errors.SchemaError):
        schema.validate(df)
