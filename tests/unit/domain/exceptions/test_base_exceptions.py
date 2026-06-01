"""Tests for base exception classes.

This module tests the hierarchical exception system and ensures
proper behavior of all exception types.
"""

from __future__ import annotations

import pytest

from bioetl.domain.exceptions.base_exceptions import (
    BioETLDomainError,
    BioETLValidationError,
    BioETLConfigurationError,
    BioETLDataQualityError,
    BioETLIntegrationError,
    BioETLNotFoundError,
    BioETLConflictError,
)


pytestmark = pytest.mark.unit

class TestBioETLDomainError:
    """Test base domain error class."""

    def test_basic_domain_error(self) -> None:
        """Test basic domain error creation."""
        error = BioETLDomainError(
            message="Test error",
            context={"key": "value"},
        )

        assert str(error).startswith("BioETLDomainError: Test error")
        assert error.message == "Test error"
        assert error.context == {"key": "value"}
        assert error.original_exception is None

    def test_domain_error_with_original_exception(self) -> None:
        """Test domain error with original exception."""
        original = ValueError("Original error")
        error = BioETLDomainError(
            message="Wrapped error",
            original_exception=original,
        )

        assert str(error).endswith("Caused by: Original error")
        assert error.original_exception is original

    def test_domain_error_to_dict(self) -> None:
        """Test domain error serialization."""
        original = ValueError("Original error")
        error = BioETLDomainError(
            message="Test error",
            context={"field": "value"},
            original_exception=original,
        )

        error_dict = error.to_dict()
        assert error_dict["error_type"] == "BioETLDomainError"
        assert error_dict["message"] == "Test error"
        assert error_dict["context"] == {"field": "value"}
        assert error_dict["original_exception"] == "Original error"
        assert error_dict["original_type"] == "ValueError"


class TestBioETLValidationError:
    """Test validation error class."""

    def test_validation_error(self) -> None:
        """Test validation error creation."""
        error = BioETLValidationError(
            message="Invalid field value",
            field_name="email",
            invalid_value="invalid@example",
        )

        assert error.field_name == "email"
        assert error.invalid_value == "invalid@example"
        assert "field_name" in error.context
        assert "invalid_value" in error.context

    def test_validation_error_with_context(self) -> None:
        """Test validation error with additional context."""
        error = BioETLValidationError(
            message="Invalid field value",
            field_name="age",
            invalid_value=-5,
            context={"min_value": 0, "max_value": 120},
        )

        assert error.context["field_name"] == "age"
        assert error.context["invalid_value"] == "-5"
        assert error.context["min_value"] == 0
        assert error.context["max_value"] == 120


class TestBioETLConfigurationError:
    """Test configuration error class."""

    def test_configuration_error(self) -> None:
        """Test configuration error creation."""
        error = BioETLConfigurationError(
            message="Missing required configuration",
            config_key="api.endpoint",
        )

        assert error.config_key == "api.endpoint"
        assert "config_key" in error.context


class TestBioETLDataQualityError:
    """Test data quality error class."""

    def test_data_quality_error(self) -> None:
        """Test data quality error creation."""
        error = BioETLDataQualityError(
            message="Invalid data format",
            record_id="record-123",
            severity="warning",
        )

        assert error.record_id == "record-123"
        assert error.severity == "warning"
        assert "record_id" in error.context
        assert "severity" in error.context

    def test_data_quality_error_invalid_severity(self) -> None:
        """Test data quality error with invalid severity."""
        with pytest.raises(ValueError, match="Invalid severity"):
            BioETLDataQualityError(
                message="Test",
                severity="invalid",
            )


class TestBioETLIntegrationError:
    """Test integration error class."""

    def test_integration_error(self) -> None:
        """Test integration error creation."""
        error = BioETLIntegrationError(
            message="Service unavailable",
            service_name="external-api",
            operation="fetch_data",
            is_retryable=True,
        )

        assert error.service_name == "external-api"
        assert error.operation == "fetch_data"
        assert error.is_retryable is True
        assert "service_name" in error.context
        assert "operation" in error.context
        assert "is_retryable" in error.context


class TestBioETLNotFoundError:
    """Test not found error class."""

    def test_not_found_error(self) -> None:
        """Test not found error creation."""
        error = BioETLNotFoundError(
            message="Resource not found",
            entity_type="User",
            entity_id="user-123",
        )

        assert error.entity_type == "User"
        assert error.entity_id == "user-123"
        assert "entity_type" in error.context
        assert "entity_id" in error.context


class TestBioETLConflictError:
    """Test conflict error class."""

    def test_conflict_error(self) -> None:
        """Test conflict error creation."""
        error = BioETLConflictError(
            message="Version conflict",
            conflicting_entity="document-v2",
        )

        assert error.conflicting_entity == "document-v2"
        assert "conflicting_entity" in error.context


class TestExceptionImmutability:
    """Test exception immutability."""

    def test_domain_error_immutability(self) -> None:
        """Test that domain errors are immutable."""
        error = BioETLDomainError(
            message="Test",
            context={"key": "value"},
        )

        # Should not be able to modify attributes
        with pytest.raises(Exception):  # dataclass frozen error
            error.message = "New message"  # type: ignore

    def test_validation_error_immutability(self) -> None:
        """Test that validation errors are immutable."""
        error = BioETLValidationError(
            message="Test",
            field_name="field",
        )

        with pytest.raises(Exception):  # dataclass frozen error
            error.field_name = "new_field"  # type: ignore
