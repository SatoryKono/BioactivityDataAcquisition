"""Public API identities must retain pair completeness and integer precision."""

import pandas as pd
import pytest

from bioetl.domain.contracts.gold._chembl_activity_assay_schemas import (
    ChEMBLAssayParametersGoldSchema,
)
from bioetl.domain.contracts.gold._chembl_reference_publication_schemas import (
    ChEMBLPublicationSimilarityGoldSchema,
)
from bioetl.domain.schemas.chembl.similarity_pair import valid_similarity_pair

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


@pytest.mark.parametrize(
    "record,expected",
    [
        ({"doc_1": 1, "doc_2": 2}, True),
        ({"doc_1": 1, "doc_2": None}, False),
        ({"publication_id1": "CHEMBL1", "publication_id2": "CHEMBL2"}, True),
        ({"publication_id1": "CHEMBL1"}, False),
        ({"publication_id1": "CHEMBL1", "doc_1": 1, "doc_2": 2}, False),
        ({"publication_id1": "CHEMBL1", "publication_id2": "CHEMBL1"}, False),
        ({"doc_1": None, "doc_2": None}, False),
    ],
)
def test_complete_pair_contract(record, expected):
    assert valid_similarity_pair(record) is expected


@pytest.mark.parametrize(
    "schema,field",
    [
        (ChEMBLAssayParametersGoldSchema, "assay_param_id"),
        (ChEMBLPublicationSimilarityGoldSchema, "sim_id"),
    ],
)
def test_gold_key_retains_low_bits_above_float_precision(schema, field):
    value = (1 << 62) + 123
    column = schema.to_schema().columns[field]
    checked = column.validate(pd.DataFrame({field: [value]}))
    assert checked[field].iloc[0] == value
    assert str(checked[field].dtype) == "int64"
