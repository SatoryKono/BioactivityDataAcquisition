"""Regression tests for confirmed Gold-contract residuals in issue #8863."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
import pytest

from bioetl.domain.contracts.gold._chembl_target_lookup_schemas import (
    ChEMBLSubcellularFractionGoldSchema,
)
from bioetl.domain.contracts.gold.composite_bioassay import CompositeTargetGoldSchema
from bioetl.domain.contracts.gold.publications_pubmed import (
    PubMedPublicationGoldSchema,
)

pytestmark = pytest.mark.unit


def _validate_column(
    model: type[pa.DataFrameModel], name: str, values: list[object]
) -> None:
    column = model.to_schema().columns[name]
    schema = pa.DataFrameSchema({name: column}, coerce=True)
    schema.validate(pd.DataFrame({name: values}))


@pytest.mark.parametrize(
    ("name", "valid", "invalid"),
    [
        ("entity_id", "0123456789abcdef", "not-a-hash"),
        ("example_assay_id", "CHEMBL12345", "ASSAY12345"),
    ],
)
def test_subcellular_lookup_identifier_formats(
    name: str,
    valid: str,
    invalid: str,
) -> None:
    _validate_column(ChEMBLSubcellularFractionGoldSchema, name, [valid])
    with pytest.raises(pa.errors.SchemaError):
        _validate_column(ChEMBLSubcellularFractionGoldSchema, name, [invalid])


@pytest.mark.parametrize(
    ("name", "valid", "invalid"),
    [("pub_month", 12.0, 1.5), ("pub_day", 31.0, 30.5)],
)
def test_pubmed_partial_dates_reject_fractional_values(
    name: str,
    valid: float,
    invalid: float,
) -> None:
    _validate_column(PubMedPublicationGoldSchema, name, [valid, None])
    with pytest.raises(pa.errors.SchemaError):
        _validate_column(PubMedPublicationGoldSchema, name, [invalid])


def test_composite_top_level_count_requires_whole_numbers() -> None:
    _validate_column(CompositeTargetGoldSchema, "top_level_count", [0.0, 3.0, None])
    with pytest.raises(pa.errors.SchemaError):
        _validate_column(CompositeTargetGoldSchema, "top_level_count", [1.5])
