"""Schema-backed validators retain missing-column and invalid-value failures."""

import pandas as pd
import pandera.pandas as pa
import pytest

from bioetl.infrastructure.validation.contract_validator import (
    ContractAwareGoldValidator,
    ContractAwareSilverValidator,
)
from bioetl.infrastructure.validation.pandera_validator import (
    BasePanderaValidator,
    PanderaGoldValidator,
    PanderaSilverValidator,
)

pytestmark = pytest.mark.unit


def test_non_strict_silver_outcomes_use_the_projected_schema_frame():
    from bioetl.domain.config.dq import DQConfig

    validator = ContractAwareSilverValidator(
        pa.DataFrameSchema({"id": pa.Column(int)}, strict=True),
        strict=False,
        dq_config=DQConfig(),
    )
    assert validator.validate_with_outcomes(
        [{"id": 1, "extra": "not-in-schema"}]
    ).is_valid


def test_silver_without_bound_policy_does_not_invent_a_contract_path():
    assert ContractAwareSilverValidator()._silver_config_path() is None


def test_base_validator_normalizes_nullable_fields_and_retains_schema_failures():
    schema = pa.DataFrameSchema(
        {"id": pa.Column(int), "optional": pa.Column(str, nullable=True)}
    )
    validator = BasePanderaValidator(schema)
    assert validator.validate([{"id": 1}]).valid
    failure = validator.validate([{"id": "invalid"}])
    assert not failure.valid and failure.errors


def test_nullable_column_seeding_without_a_schema_preserves_input_identity():
    frame = pd.DataFrame({"id": [1]})
    assert BasePanderaValidator()._seed_missing_nullable_columns(frame) is frame


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
