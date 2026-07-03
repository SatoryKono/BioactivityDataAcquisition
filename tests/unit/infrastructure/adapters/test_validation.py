"""Tests for shared validation utilities.

Tests API response parsing with Pydantic models and graceful error handling.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field

from bioetl.infrastructure.adapters.validation import (
    RecordValidationResult,
    get_record_model,
    parse_with_validation,
    validate_record,
    validate_records,
)


class SampleModel(BaseModel):
    """Sample Pydantic model for testing."""

    id: str
    name: str
    value: int = Field(ge=0)
    optional_field: str | None = None


@pytest.mark.unit
class TestRecordValidationResult:
    """Test RecordValidationResult dataclass."""

    def test_validation_result__default_values__120cfcf3(self) -> None:
        """Test default field values."""
        result = RecordValidationResult()
        assert result.record is None
        assert result.validated is None
        assert result.is_valid is False
        assert result.error is None
        assert result.error_details == []

    def test_successful_validation(self) -> None:
        """Test successful validation result."""
        model = SampleModel(id="1", name="test", value=10)
        result = RecordValidationResult(
            record={"id": "1", "name": "test", "value": 10},
            validated=model,
            is_valid=True,
        )
        assert result.is_valid is True
        assert result.validated is not None
        assert result.error is None

    def test_failed_validation(self) -> None:
        """Test failed validation result."""
        result = RecordValidationResult(
            record={"id": "1"},
            validated=None,
            is_valid=False,
            error="Missing required field: name",
            error_details=[{"loc": ["name"], "msg": "Field required"}],
        )
        assert result.is_valid is False
        assert result.validated is None
        assert result.error is not None
        assert len(result.error_details) == 1


@pytest.mark.unit
class TestValidateRecord:
    """Test validate_record function."""

    def test_validate_record__validation__865ac5f8(self) -> None:
        """Test successful record validation."""
        record: dict[str, Any] = {"id": "1", "name": "test", "value": 10}
        result = validate_record(record, SampleModel)

        assert result.is_valid is True
        assert result.validated is not None
        assert isinstance(result.validated, SampleModel)
        assert result.validated.id == "1"
        assert result.error is None

    def test_validation_with_optional_field(self) -> None:
        """Test validation with optional field present."""
        record: dict[str, Any] = {
            "id": "1",
            "name": "test",
            "value": 10,
            "optional_field": "extra",
        }
        result = validate_record(record, SampleModel)

        assert result.is_valid is True
        assert result.validated is not None
        assert result.validated.optional_field == "extra"

    def test_failed_validation_missing_field(self) -> None:
        """Test validation failure due to missing required field."""
        record: dict[str, Any] = {"id": "1"}  # Missing name and value
        result = validate_record(record, SampleModel)

        assert result.is_valid is False
        assert result.validated is None
        assert result.error is not None
        assert "errors" in result.error.lower()
        assert len(result.error_details) >= 1

    def test_failed_validation_invalid_type(self) -> None:
        """Test validation failure due to invalid type."""
        record: dict[str, Any] = {"id": "1", "name": "test", "value": "not_an_int"}
        result = validate_record(record, SampleModel)

        assert result.is_valid is False
        assert result.validated is None

    def test_failed_validation_constraint_violation(self) -> None:
        """Test validation failure due to constraint violation."""
        record: dict[str, Any] = {"id": "1", "name": "test", "value": -1}
        result = validate_record(record, SampleModel)

        assert result.is_valid is False
        assert result.validated is None

    def test_validation_with_logger(self) -> None:
        """Test validation logs warning on failure."""
        logger = MagicMock()
        record: dict[str, Any] = {"id": "1"}  # Invalid

        validate_record(record, SampleModel, logger=logger, context="test_context")

        logger.warning.assert_called_once()
        call_args = logger.warning.call_args
        assert call_args[0][0] == "api_record_validation_failed"
        assert call_args[1]["context"] == "test_context"

    def test_validation_without_logger(self) -> None:
        """Test validation works without logger."""
        record: dict[str, Any] = {"id": "1"}  # Invalid
        result = validate_record(record, SampleModel)

        assert result.is_valid is False
        # Should not raise even without logger

    def test_error_details_structure(self) -> None:
        """Test error details contain expected fields."""
        record: dict[str, Any] = {"id": "1"}  # Missing name
        result = validate_record(record, SampleModel)

        assert len(result.error_details) >= 1
        detail = result.error_details[0]
        assert "loc" in detail
        assert "msg" in detail
        assert "type" in detail


@pytest.mark.unit
class TestValidateRecords:
    """Test validate_records function."""

    def test_validate_multiple_records(self) -> None:
        """Test validating multiple records."""
        records: list[dict[str, Any]] = [
            {"id": "1", "name": "test1", "value": 10},
            {"id": "2", "name": "test2", "value": 20},
        ]

        results = list(validate_records(records, SampleModel))

        assert len(results) == 2
        assert all(r.is_valid for r in results)

    def test_mixed_valid_invalid_records(self) -> None:
        """Test validation of mixed valid/invalid records."""
        records: list[dict[str, Any]] = [
            {"id": "1", "name": "valid", "value": 10},
            {"id": "2"},  # Invalid - missing fields
            {"id": "3", "name": "valid2", "value": 30},
        ]

        results = list(validate_records(records, SampleModel))

        assert len(results) == 3
        assert results[0].is_valid is True
        assert results[1].is_valid is False
        assert results[2].is_valid is True

    def test_validate_records__empty_records__e99fec9b(self) -> None:
        """Test validation of empty record list."""
        results = list(validate_records([], SampleModel))
        assert results == []

    def test_yields_results_lazily(self) -> None:
        """Test that results are yielded lazily."""
        records: list[dict[str, Any]] = [
            {"id": str(i), "name": f"test{i}", "value": i} for i in range(100)
        ]

        # Generator should not consume all records immediately
        gen = validate_records(records, SampleModel)
        first = next(gen)
        assert first.is_valid is True


@pytest.mark.unit
class TestParseWithValidation:
    """Test parse_with_validation function."""

    def test_valid_record_returns_model_dump(self) -> None:
        """Test valid record returns model_dump dict."""
        record: dict[str, Any] = {"id": "1", "name": "test", "value": 10}
        result = parse_with_validation(record, SampleModel)

        assert isinstance(result, dict)
        assert result["id"] == "1"
        assert result["name"] == "test"
        assert result["value"] == 10

    def test_invalid_record_graceful_mode_returns_original(self) -> None:
        """Test invalid record in graceful mode returns original."""
        record: dict[str, Any] = {"id": "1", "invalid_field": "data"}
        result = parse_with_validation(record, SampleModel, strict=False)

        # Should return original record unchanged
        assert result == record

    def test_invalid_record_strict_mode_raises(self) -> None:
        """Test invalid record in strict mode raises ValueError."""
        record: dict[str, Any] = {"id": "1"}  # Invalid

        with pytest.raises(ValueError) as exc_info:
            parse_with_validation(record, SampleModel, strict=True)

        assert "validation failed" in str(exc_info.value).lower()

    def test_with_logger(self) -> None:
        """Test parse_with_validation uses logger."""
        logger = MagicMock()
        record: dict[str, Any] = {"id": "1"}  # Invalid

        parse_with_validation(
            record,
            SampleModel,
            strict=False,
            logger=logger,
            context="test",
        )

        logger.warning.assert_called_once()


@pytest.mark.unit
class TestGetRecordModel:
    """Test get_record_model function."""

    def test_chembl_activity_model(self) -> None:
        """Test getting ChEMBL activity model."""
        model = get_record_model("chembl", "activity")
        # Should return a model class or None (depending on registration)
        # Just verify it doesn't raise
        assert model is None or issubclass(model, BaseModel)

    def test_pubchem_model(self) -> None:
        """Test getting PubChem model."""
        model = get_record_model("pubchem", "compound")
        assert model is None or issubclass(model, BaseModel)

    def test_uniprot_model(self) -> None:
        """Test getting UniProt model."""
        model = get_record_model("uniprot", "protein")
        assert model is None or issubclass(model, BaseModel)

    def test_pubmed_model(self) -> None:
        """Test getting PubMed model."""
        model = get_record_model("pubmed", "publication")
        assert model is None or issubclass(model, BaseModel)

    def test_crossref_model(self) -> None:
        """Test getting CrossRef model."""
        model = get_record_model("crossref", "work")
        assert model is None or issubclass(model, BaseModel)

    def test_unknown_provider_returns_none(self) -> None:
        """Test unknown provider returns None."""
        model = get_record_model("unknown_provider", "entity")
        assert model is None

    def test_unknown_entity_returns_none(self) -> None:
        """Test unknown entity type returns None."""
        model = get_record_model("chembl", "unknown_entity_type")
        assert model is None
