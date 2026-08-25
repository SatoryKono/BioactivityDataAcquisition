# pyright: reportArgumentType=false
"""Entity primary keys declare unique=True (#9635)."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
import pytest

from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.publication_term import PublicationTermSchema


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
