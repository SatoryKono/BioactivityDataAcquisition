"""Unit tests for Pandera validators.

Tests for PanderaSilverValidator, PanderaGoldValidator, and their NoOp counterparts.
"""

from __future__ import annotations

import warnings

import pytest

from bioetl.domain.types import ValidationResult
from bioetl.infrastructure.validation.pandera_validator import (
    NoOpGoldValidator,
    NoOpSilverValidator,
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


@pytest.mark.unit
class TestNoOpSilverValidator:
    """Tests for NoOpSilverValidator."""

    def test_validate_always_returns_valid(self):
        """Test that NoOpSilverValidator always returns valid."""
        validator = NoOpSilverValidator()
        records = [{"entity_id": "CHEMBL123", "invalid_field": "xyz"}]
        result = validator.validate(records)
        assert result.valid is True
        assert result.errors == []

    def test_validate_empty_records_returns_valid(self):
        """Test that empty records also returns valid."""
        validator = NoOpSilverValidator()
        result = validator.validate([])
        assert result.valid is True
        assert result.errors == []

    def test_implements_validation_result_protocol(self):
        """Test that validate returns ValidationResult type."""
        validator = NoOpSilverValidator()
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
class TestNoOpGoldValidator:
    """Tests for NoOpGoldValidator."""

    def test_validate_always_returns_valid(self):
        """Test that NoOpGoldValidator always returns valid."""
        validator = NoOpGoldValidator()
        records = [{"entity_id": "CHEMBL123", "invalid_field": "xyz"}]
        result = validator.validate(records)
        assert result.valid is True
        assert result.errors == []

    def test_implements_validation_result_protocol(self):
        """Test that validate returns ValidationResult type."""
        validator = NoOpGoldValidator()
        result = validator.validate([{"test": "data"}])
        assert isinstance(result, ValidationResult)


@pytest.mark.unit
class TestSilverValidatorPortProtocol:
    """Tests for SilverValidatorPort protocol compliance."""

    def test_pandera_silver_validator_is_runtime_checkable(self):
        """Test that PanderaSilverValidator can be runtime checked."""
        from bioetl.domain.ports.validation import SilverValidatorPort

        validator = PanderaSilverValidator()
        assert isinstance(validator, SilverValidatorPort)

    def test_noop_silver_validator_is_runtime_checkable(self):
        """Test that NoOpSilverValidator can be runtime checked."""
        from bioetl.domain.ports.validation import SilverValidatorPort

        validator = NoOpSilverValidator()
        assert isinstance(validator, SilverValidatorPort)


@pytest.mark.unit
class TestGoldValidatorPortProtocol:
    """Tests for GoldValidatorPort protocol compliance."""

    def test_pandera_gold_validator_is_runtime_checkable(self):
        """Test that PanderaGoldValidator can be runtime checked."""
        from bioetl.domain.ports.validation import GoldValidatorPort

        validator = PanderaGoldValidator()
        assert isinstance(validator, GoldValidatorPort)

    def test_noop_gold_validator_is_runtime_checkable(self):
        """Test that NoOpGoldValidator can be runtime checked."""
        from bioetl.domain.ports.validation import GoldValidatorPort

        validator = NoOpGoldValidator()
        assert isinstance(validator, GoldValidatorPort)
