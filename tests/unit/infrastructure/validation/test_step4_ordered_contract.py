"""Ordered schemas validate supplied order before synthesized nullable fields."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pandera.pandas as pa
import pytest

from bioetl.domain.exceptions import SchemaViolationError
from bioetl.infrastructure.validation.pandera_validator import (
    PanderaGoldValidator,
    PanderaSilverValidator,
)
from bioetl.infrastructure.storage.silver.merged_operations import (
    _MergedSilverWriteRequest,
    _prepare_merged_silver_write,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("validator", [PanderaGoldValidator, PanderaSilverValidator])
@pytest.mark.parametrize("strict", [True, False])
@pytest.mark.parametrize("ordered", [True, False])
@pytest.mark.parametrize("columns", [("a", "b", "c"), ("c", "a", "b")])
def test_supplied_order_is_not_repaired(validator, strict, ordered, columns):
    schema = pa.DataFrameSchema(
        {c: pa.Column(int) for c in ("a", "b", "c")}, ordered=ordered, strict=True
    )
    result = validator(schema=schema, strict=strict).validate(
        [dict.fromkeys(columns, 1)]
    )
    assert result.valid is (not ordered or columns == ("a", "b", "c"))


@pytest.mark.parametrize("validator", [PanderaGoldValidator, PanderaSilverValidator])
@pytest.mark.parametrize("strict", [True, False])
def test_nullable_insertion_respects_present_fields_and_extras(validator, strict):
    schema = pa.DataFrameSchema(
        {
            "a": pa.Column(int),
            "b": pa.Column(float, nullable=True, coerce=True),
            "c": pa.Column(int),
            "d": pa.Column(float, nullable=True, coerce=True),
            "e": pa.Column(int),
        },
        ordered=True,
        strict=False,
    )
    result = validator(schema=schema, strict=strict).validate(
        [{"a": 1, "extra": 9, "c": 3, "e": 5}]
    )
    assert result.valid, result.errors


@pytest.mark.parametrize("validator", [PanderaGoldValidator, PanderaSilverValidator])
def test_non_strict_filter_keeps_wrong_order(validator):
    schema = pa.DataFrameSchema(
        {c: pa.Column(int) for c in ("a", "b", "c")}, ordered=True, strict=True
    )
    result = validator(schema=schema, strict=False).validate(
        [{"c": 3, "a": 1, "b": 2, "extra": 9}]
    )
    assert not result.valid
    assert "column" in str(result.errors).lower()


def test_merged_silver_rejects_wrong_order_before_arrow_conversion():
    schema = pa.DataFrameSchema(
        {c: pa.Column(int) for c in ("a", "b", "c")}, ordered=True, strict=True
    )
    converter = MagicMock()
    host = SimpleNamespace(
        _arrow_converter=converter, _resolve_table_path=lambda _: "unused"
    )
    request = _MergedSilverWriteRequest(
        table_name="synthetic",
        records=[{"c": 3, "a": 1, "b": 2, "extra": 9}],
        schema=schema,
    )
    with pytest.raises(SchemaViolationError):
        _prepare_merged_silver_write(host, request)
    converter.convert_records_to_arrow.assert_not_called()


@pytest.mark.parametrize("validator", [PanderaGoldValidator, PanderaSilverValidator])
@pytest.mark.parametrize("strict", [True, False])
@pytest.mark.parametrize("dtype", ["Int64", "boolean"])
def test_nullable_extension_dtype_insertions_validate_without_reordering(
    validator, strict, dtype
):
    schema = pa.DataFrameSchema(
        {
            "a": pa.Column(int),
            "b": pa.Column(dtype, nullable=True),
            "c": pa.Column(int),
            "d": pa.Column(dtype, nullable=True),
            "e": pa.Column(int),
        },
        ordered=True,
        strict=False,
    )
    valid = validator(schema=schema, strict=strict).validate(
        [{"a": 1, "extra": 9, "c": 3, "e": 5}]
    )
    assert valid.valid, valid.errors
    invalid = validator(schema=schema, strict=strict).validate(
        [{"c": 3, "a": 1, "extra": 9, "e": 5}]
    )
    assert not invalid.valid


@pytest.mark.parametrize("strict", [True, False])
@pytest.mark.parametrize("dtype", ["Int64", "boolean"])
def test_contract_aware_gold_policy_path_preserves_order_and_nullable_dtype(
    strict, dtype
):
    from bioetl.infrastructure.validation.contract_validator import (
        ContractAwareGoldValidator,
    )
    from bioetl.domain.config.dq import DQConfig

    schema = pa.DataFrameSchema(
        {
            "a": pa.Column(int),
            "b": pa.Column(dtype, nullable=True),
            "c": pa.Column(int),
            "d": pa.Column(dtype, nullable=True),
            "e": pa.Column(int),
        },
        ordered=True,
        strict=False,
    )
    validator = ContractAwareGoldValidator(
        schema=schema, strict=strict, dq_config=DQConfig()
    )
    good, outcomes = validator.validate_with_outcomes(
        [{"a": 1, "extra": 9, "c": 3, "e": 5}]
    )
    assert good, outcomes
    bad, outcomes = validator.validate_with_outcomes(
        [{"c": 3, "a": 1, "extra": 9, "e": 5}]
    )
    assert not bad
    assert outcomes
