"""Unit tests for Pandera validators.

Tests for PanderaSilverValidator, PanderaGoldValidator, and NoOpValidator.
Includes property-based tests using Hypothesis for robustness validation.
"""

from __future__ import annotations

import warnings

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bioetl.domain.types import ValidationResult
from bioetl.infrastructure.validation.pandera_validator import (
    NoOpValidator,
    PanderaGoldValidator,
    PanderaSilverValidator,
)


@pytest.fixture(autouse=True)
def suppress_pandera_future_warnings():
    """Suppress Pandera import FutureWarnings during tests."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning, module="pandera")
        yield


@pytest.mark.unit
class TestPanderaSilverValidator:
    """Tests for PanderaSilverValidator."""

    def test_validate_empty_records_returns_valid(self):
        """Test that empty records list returns valid result."""
        validator = PanderaSilverValidator()
        result = validator.validate([])
        assert result.valid is True
        assert result.errors == []

    def test_validate_without_schema_returns_valid(self):
        """Test that validation without schema returns valid (non-strict mode)."""
        validator = PanderaSilverValidator(schema=None, strict=False)
        records = [{"entity_id": "CHEMBL123", "value": 5.5}]
        result = validator.validate(records)
        assert result.valid is True
        assert result.errors == []

    def test_validate_without_schema_strict_mode_returns_invalid(self):
        """Test that validation without schema in strict mode returns invalid."""
        validator = PanderaSilverValidator(schema=None, strict=True)
        records = [{"entity_id": "CHEMBL123", "value": 5.5}]
        result = validator.validate(records)
        assert result.valid is False
        assert "Silver schema is required but not provided" in result.errors

    def test_validate_with_schema_valid_records(self):
        """Test validation passes for records matching schema."""
        import pandera as pa

        schema = pa.DataFrameSchema(
            {
                "entity_id": pa.Column(str),
                "value": pa.Column(float),
            }
        )
        validator = PanderaSilverValidator(schema=schema)
        records = [
            {"entity_id": "CHEMBL123", "value": 5.5},
            {"entity_id": "CHEMBL456", "value": 7.2},
        ]
        result = validator.validate(records)
        assert result.valid is True
        assert result.errors == []

    def test_validate_with_schema_invalid_records(self):
        """Test validation fails for records not matching schema."""
        import pandera as pa

        schema = pa.DataFrameSchema(
            {
                "entity_id": pa.Column(str),
                "value": pa.Column(float, checks=pa.Check.ge(0)),
            }
        )
        validator = PanderaSilverValidator(schema=schema)
        records = [
            {"entity_id": "CHEMBL123", "value": -5.5},  # Negative value should fail
        ]
        result = validator.validate(records)
        assert result.valid is False
        assert len(result.errors) > 0

    def test_validate_with_schema_missing_column(self):
        """Test validation fails when required column is missing."""
        import pandera as pa

        schema = pa.DataFrameSchema(
            {
                "entity_id": pa.Column(str),
                "required_field": pa.Column(str),
            }
        )
        validator = PanderaSilverValidator(schema=schema)
        records = [
            {"entity_id": "CHEMBL123"},  # Missing required_field
        ]
        result = validator.validate(records)
        assert result.valid is False
        assert len(result.errors) > 0

    def test_validate_with_nullable_columns(self):
        """Test validation passes with nullable columns when using valid types."""
        import math

        import pandera as pa

        schema = pa.DataFrameSchema(
            {
                "entity_id": pa.Column(str),
                "optional_value": pa.Column(float, nullable=True),
            }
        )
        validator = PanderaSilverValidator(schema=schema)
        # Use NaN instead of None to maintain float64 dtype
        records = [
            {"entity_id": "CHEMBL123", "optional_value": math.nan},
            {"entity_id": "CHEMBL456", "optional_value": 5.5},
        ]
        result = validator.validate(records)
        assert result.valid is True

    def test_validate_with_ordered_schema_reorders_columns(self):
        """Columns in wrong order pass validation after reorder."""
        import pandera as pa

        schema = pa.DataFrameSchema(
            columns={
                "a": pa.Column(str),
                "b": pa.Column(int),
                "c": pa.Column(float),
            },
            ordered=True,
            strict=True,
        )
        validator = PanderaSilverValidator(schema=schema)
        # Records with columns in WRONG order (c, a, b instead of a, b, c)
        records = [{"c": 1.0, "a": "x", "b": 1}]
        result = validator.validate(records)
        assert result.valid is True

    def test_validate_chembl_target_all_null_nullable_boolean_batch(self):
        """chembl.target accepts batches where nullable bool stays null for all rows."""
        from bioetl.domain.schemas.chembl.target import TargetSchema

        validator = PanderaSilverValidator(schema=TargetSchema.to_schema())
        records = [
            {
                "entity_id": "chembl_target:CHEMBL1",
                "content_hash": "a" * 64,
                "_run_id": "run-1",
                "_run_type": "backfill",
                "_source_batch_id": "batch-1",
                "_ingestion_ts": "2026-05-11T14:55:44Z",
                "_index": 0,
                "_dq_warn": False,
                "_dq_error": False,
                "target_id": "CHEMBL1",
                "target_type": "SINGLE PROTEIN",
                "pref_name": "Target one",
                "organism": "Homo sapiens",
                "species_group_flag": False,
                "downgraded": None,
            },
            {
                "entity_id": "chembl_target:CHEMBL2",
                "content_hash": "b" * 64,
                "_run_id": "run-1",
                "_run_type": "backfill",
                "_source_batch_id": "batch-1",
                "_ingestion_ts": "2026-05-11T14:55:45Z",
                "_index": 1,
                "_dq_warn": False,
                "_dq_error": False,
                "target_id": "CHEMBL2",
                "target_type": "SINGLE PROTEIN",
                "pref_name": "Target two",
                "organism": "Homo sapiens",
                "species_group_flag": False,
                "downgraded": None,
            },
        ]

        result = validator.validate(records)
        assert result.valid is True
        assert result.errors == []


@pytest.mark.unit
class TestNoOpValidator:
    """Tests for the shared NoOpValidator."""

    def test_validate_always_returns_valid(self):
        """Test that NoOpValidator always returns valid."""
        validator = NoOpValidator()
        records = [{"entity_id": "CHEMBL123", "invalid_field": "xyz"}]
        result = validator.validate(records)
        assert result.valid is True
        assert result.errors == []

    def test_validate_empty_records_returns_valid(self):
        """Test that empty records also returns valid."""
        validator = NoOpValidator()
        result = validator.validate([])
        assert result.valid is True
        assert result.errors == []

    def test_implements_validation_result_protocol(self):
        """Test that validate returns ValidationResult type."""
        validator = NoOpValidator()
        result = validator.validate([{"test": "data"}])
        assert isinstance(result, ValidationResult)


@pytest.mark.unit
class TestPanderaGoldValidator:
    """Tests for PanderaGoldValidator."""

    def test_validate_empty_records_returns_valid(self):
        """Test that empty records list returns valid result."""
        validator = PanderaGoldValidator()
        result = validator.validate([])
        assert result.valid is True
        assert result.errors == []

    def test_validate_without_schema_returns_valid(self):
        """Test that validation without schema returns valid (non-strict mode)."""
        validator = PanderaGoldValidator(schema=None, strict=False)
        records = [{"entity_id": "CHEMBL123", "value": 5.5}]
        result = validator.validate(records)
        assert result.valid is True
        assert result.errors == []

    def test_validate_without_schema_strict_mode_returns_invalid(self):
        """Test that validation without schema in strict mode returns invalid."""
        validator = PanderaGoldValidator(schema=None, strict=True)
        records = [{"entity_id": "CHEMBL123", "value": 5.5}]
        result = validator.validate(records)
        assert result.valid is False
        assert "Gold schema is required but not provided" in result.errors

    def test_validate_with_schema_valid_records(self):
        """Test validation passes for records matching schema."""
        import pandera as pa

        schema = pa.DataFrameSchema(
            {
                "entity_id": pa.Column(str),
                "value": pa.Column(float),
            }
        )
        validator = PanderaGoldValidator(schema=schema)
        records = [
            {"entity_id": "CHEMBL123", "value": 5.5},
            {"entity_id": "CHEMBL456", "value": 7.2},
        ]
        result = validator.validate(records)
        assert result.valid is True
        assert result.errors == []


@pytest.mark.unit
class TestSilverValidatorPortProtocol:
    """Tests for SilverValidatorPort protocol compliance."""

    def test_pandera_silver_validator_is_runtime_checkable(self):
        """Test that PanderaSilverValidator can be runtime checked."""
        from bioetl.domain.ports import SilverValidatorPort

        validator = PanderaSilverValidator()
        assert isinstance(validator, SilverValidatorPort)

    def test_noop_silver_validator_is_runtime_checkable(self):
        """Test that NoOpValidator can be runtime checked as SilverValidatorPort."""
        from bioetl.domain.ports import SilverValidatorPort

        validator = NoOpValidator()
        assert isinstance(validator, SilverValidatorPort)


@pytest.mark.unit
class TestGoldValidatorPortProtocol:
    """Tests for GoldValidatorPort protocol compliance."""

    def test_pandera_gold_validator_is_runtime_checkable(self):
        """Test that PanderaGoldValidator can be runtime checked."""
        from bioetl.domain.ports import GoldValidatorPort

        validator = PanderaGoldValidator()
        assert isinstance(validator, GoldValidatorPort)

    def test_noop_gold_validator_is_runtime_checkable(self):
        """Test that NoOpValidator can be runtime checked as GoldValidatorPort."""
        from bioetl.domain.ports import GoldValidatorPort

        validator = NoOpValidator()
        assert isinstance(validator, GoldValidatorPort)


# JSON-compatible primitive types for property-based testing
json_primitive = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=100),
)

# Recursive JSON-like structure (limited depth for performance)
json_value = st.recursive(
    json_primitive,
    lambda children: (
        st.lists(children, max_size=5)
        | st.dictionaries(st.text(max_size=20), children, max_size=5)
    ),
    max_leaves=10,
)

# Strategy for generating arbitrary records
arbitrary_record = st.dictionaries(
    keys=st.text(min_size=1, max_size=30),
    values=json_value,
    min_size=1,
    max_size=10,
)


@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.hypothesis
class TestPanderaValidatorPropertyBased:
    """Property-based tests for Pandera validators using Hypothesis.

    These tests verify that validators handle arbitrary input gracefully
    without raising unexpected exceptions.

    Note: max_examples is controlled by Hypothesis profile (conftest.py):
    - CI: 10 examples (fast)
    - fast: 5 examples (smoke tests)
    - dev: 50 examples (default)
    - thorough: 200 examples (pre-release)
    """

    @given(records=st.lists(arbitrary_record, max_size=10))
    @settings(
        deadline=None,
        max_examples=10,  # Limit examples to avoid pytest timeout
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    )
    def test_silver_validator_never_raises_on_arbitrary_input(
        self, records: list[dict]
    ):
        """Property: SilverValidator.validate() never raises on any input.

        For any list of dictionaries, validate() should return a ValidationResult
        (valid or invalid), not raise an exception.
        """
        validator = PanderaSilverValidator(schema=None, strict=False)
        result = validator.validate(records)
        assert isinstance(result, ValidationResult)
        assert isinstance(result.valid, bool)
        assert isinstance(result.errors, list)

    @given(records=st.lists(arbitrary_record, max_size=10))
    @settings(
        deadline=None,
        max_examples=10,  # Limit examples to avoid pytest timeout
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    )
    def test_gold_validator_never_raises_on_arbitrary_input(self, records: list[dict]):
        """Property: GoldValidator.validate() never raises on any input.

        For any list of dictionaries, validate() should return a ValidationResult
        (valid or invalid), not raise an exception.
        """
        validator = PanderaGoldValidator(schema=None, strict=False)
        result = validator.validate(records)
        assert isinstance(result, ValidationResult)
        assert isinstance(result.valid, bool)
        assert isinstance(result.errors, list)

    @given(records=st.lists(arbitrary_record, max_size=10))
    @settings(
        deadline=None,
        max_examples=10,  # Limit examples to avoid pytest timeout
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    )
    def test_noop_validators_always_return_valid(self, records: list[dict]):
        """Property: NoOp validators always return valid=True for any input."""
        silver_validator = NoOpValidator()
        gold_validator = NoOpValidator()

        silver_result = silver_validator.validate(records)
        gold_result = gold_validator.validate(records)

        assert silver_result.valid is True
        assert silver_result.errors == []
        assert gold_result.valid is True
        assert gold_result.errors == []

    @given(records=st.lists(arbitrary_record, max_size=10))
    @settings(
        deadline=None,
        max_examples=10,  # Limit examples to avoid pytest timeout
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
    )
    def test_strict_mode_without_schema_always_fails(self, records: list[dict]):
        """Property: Strict mode without schema returns invalid for non-empty input."""
        if not records:
            return  # Skip empty records - edge case handled separately

        silver_validator = PanderaSilverValidator(schema=None, strict=True)
        gold_validator = PanderaGoldValidator(schema=None, strict=True)

        silver_result = silver_validator.validate(records)
        gold_result = gold_validator.validate(records)

        assert silver_result.valid is False
        assert gold_result.valid is False

    @given(
        record=st.fixed_dictionaries(
            {
                "entity_id": st.text(min_size=1, max_size=50),
                "value": st.floats(allow_nan=False, allow_infinity=False),
            }
        )
    )
    @settings(deadline=None)
    def test_valid_records_pass_matching_schema(self, record: dict):
        """Property: Records matching schema structure always pass validation."""
        import pandera as pa

        schema = pa.DataFrameSchema(
            {
                "entity_id": pa.Column(str),
                "value": pa.Column(float),
            }
        )
        validator = PanderaSilverValidator(schema=schema)
        result = validator.validate([record])
        assert result.valid is True
        assert result.errors == []
