"""Unit tests for GoldValidator."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.core.gold_validator import GoldValidator, ValidationResult


@pytest.mark.unit
class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid result."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []

    def test_invalid_result_with_errors(self):
        """Test creating an invalid result with errors."""
        errors = ["Error 1", "Error 2"]
        result = ValidationResult(valid=False, errors=errors)
        assert result.valid is False
        assert result.errors == errors

    def test_result_is_immutable(self):
        """Test that ValidationResult is immutable (frozen)."""
        result = ValidationResult(valid=True)
        with pytest.raises(AttributeError):
            result.valid = False  # type: ignore[misc]


@pytest.mark.unit
class TestGoldValidatorInit:
    """Tests for GoldValidator initialization."""

    def test_init_with_schema(self):
        """Test initialization with a schema."""
        mock_schema = MagicMock()
        validator = GoldValidator(mock_schema)
        assert validator._schema is mock_schema

    def test_init_without_schema(self):
        """Test initialization without a schema."""
        validator = GoldValidator(None)
        assert validator._schema is None


@pytest.mark.unit
class TestGoldValidatorValidate:
    """Tests for GoldValidator.validate method."""

    def test_validate_without_schema_returns_valid(self):
        """Test that validation without schema always returns valid."""
        validator = GoldValidator(None)
        records = [{"id": 1, "value": "test"}]

        result = validator.validate(records)

        assert result.valid is True
        assert result.errors == []

    def test_validate_empty_records_returns_valid(self):
        """Test that validation of empty records always returns valid."""
        mock_schema = MagicMock()
        validator = GoldValidator(mock_schema)

        result = validator.validate([])

        assert result.valid is True
        assert result.errors == []
        mock_schema.validate.assert_not_called()

    def test_validate_with_valid_records(self):
        """Test validation with valid records."""
        mock_schema = MagicMock()
        mock_schema.validate.return_value = MagicMock()  # No exception = valid
        validator = GoldValidator(mock_schema)
        records = [{"id": 1, "value": "test"}]

        result = validator.validate(records)

        assert result.valid is True
        assert result.errors == []
        mock_schema.validate.assert_called_once()

    def test_validate_with_invalid_records(self):
        """Test validation with invalid records."""
        mock_schema = MagicMock()
        mock_schema.validate.side_effect = ValueError("Schema validation failed: missing 'name'")
        validator = GoldValidator(mock_schema)
        records = [{"id": 1}]  # Missing 'name' field

        result = validator.validate(records)

        assert result.valid is False
        assert len(result.errors) == 1
        assert "Schema validation failed" in result.errors[0]

    def test_validate_converts_records_to_dataframe(self):
        """Test that records are converted to DataFrame for validation."""
        mock_schema = MagicMock()
        validator = GoldValidator(mock_schema)
        records = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]

        validator.validate(records)

        # Verify DataFrame was passed to validate
        call_args = mock_schema.validate.call_args
        df = call_args[0][0]  # First positional argument
        assert len(df) == 2
        assert list(df.columns) == ["id", "name"]

    def test_validate_uses_lazy_mode(self):
        """Test that validation uses lazy=True."""
        mock_schema = MagicMock()
        validator = GoldValidator(mock_schema)
        records = [{"id": 1}]

        validator.validate(records)

        mock_schema.validate.assert_called_once()
        call_kwargs = mock_schema.validate.call_args[1]
        assert call_kwargs.get("lazy") is True

    def test_validate_captures_multiple_errors(self):
        """Test that validation captures error message from exception."""
        mock_schema = MagicMock()
        error_message = "Multiple errors: field1 invalid, field2 missing"
        mock_schema.validate.side_effect = Exception(error_message)
        validator = GoldValidator(mock_schema)
        records = [{"id": 1}]

        result = validator.validate(records)

        assert result.valid is False
        assert error_message in result.errors[0]


@pytest.mark.unit
class TestGoldValidatorIntegration:
    """Integration-like tests for GoldValidator with real Pandera schema."""

    def test_validate_with_pandera_schema_valid(self):
        """Test validation with a real Pandera schema - valid case."""
        import pandera.pandas as pa

        schema = pa.DataFrameSchema(
            {
                "id": pa.Column(int),
                "name": pa.Column(str),
            }
        )
        validator = GoldValidator(schema)
        records = [
            {"id": 1, "name": "test1"},
            {"id": 2, "name": "test2"},
        ]

        result = validator.validate(records)

        assert result.valid is True
        assert result.errors == []

    def test_validate_with_pandera_schema_invalid(self):
        """Test validation with a real Pandera schema - invalid case."""
        import pandera.pandas as pa

        schema = pa.DataFrameSchema(
            {
                "id": pa.Column(int),
                "name": pa.Column(str),
            }
        )
        validator = GoldValidator(schema)
        records = [
            {"id": "not_an_int", "name": "test1"},  # Invalid: id should be int
        ]

        result = validator.validate(records)

        assert result.valid is False
        assert len(result.errors) > 0
