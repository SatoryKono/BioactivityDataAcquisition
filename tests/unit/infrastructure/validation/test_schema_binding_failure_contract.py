"""Schema-backed validators retain missing-column and invalid-value failures."""

import pandas as pd
import pandera.pandas as pa
import pytest

from bioetl.infrastructure.validation.contract_validator import (
    ContractAwareGoldValidator,
)
from bioetl.infrastructure.validation.pandera_validator import (
    PanderaGoldValidator,
    PanderaSilverValidator,
)

pytestmark = pytest.mark.unit


def test_gold_validator_accepts_valid_values_and_rejects_schema_failure():
    schema = pa.DataFrameSchema({"id": pa.Column(int)})
    validator = PanderaGoldValidator(schema)
    assert validator.validate([{"id": 1}]).valid is True
    result = validator.validate([{"id": "invalid"}])
    assert result.valid is False
    assert result.errors


def test_ordered_non_strict_silver_does_not_invent_a_required_value():
    schema = pa.DataFrameSchema(
        {"id": pa.Column(int), "required": pa.Column(int, nullable=False)}, ordered=True
    )
    validator = PanderaSilverValidator(schema, strict=False)
    result = validator.validate([{"id": 1}])
    assert result.valid is False
    assert result.errors


def test_contract_gold_preserves_named_index_column_when_dropping_extras():
    schema = pa.DataFrameSchema(
        {"value": pa.Column(int)}, index=pa.Index(int, name="entity_id")
    )
    validator = ContractAwareGoldValidator(schema, strict=False)
    frame = pd.DataFrame({"value": [1], "entity_id": [2], "extra": [3]})
    prepared = validator._prepare_df_for_validation(frame)
    assert prepared["entity_id"].tolist() == [2]
    assert prepared["value"].tolist() == [1]
    assert "extra" not in prepared.columns
