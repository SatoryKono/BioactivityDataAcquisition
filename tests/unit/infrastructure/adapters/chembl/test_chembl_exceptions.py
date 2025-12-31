"""Tests for ChEMBL-specific exceptions.

These tests ensure that ChEMBL adapter exceptions:
1. Inherit from proper base classes
2. Have correct error types
3. Preserve all necessary context
"""

from __future__ import annotations

import pytest

from bioetl.domain.exceptions import ExternalServiceError
from bioetl.domain.types import ErrorType
from bioetl.infrastructure.adapters.chembl.exceptions import (
    ChemblApiError,
    ChemblAuthError,
    ChemblRateLimitError,
    ChemblServiceUnavailableError,
)


@pytest.mark.unit
class TestChemblApiError:
    """Test ChemblApiError base exception."""

    def test_inherits_from_external_service_error(self) -> None:
        """Test that ChemblApiError inherits from ExternalServiceError."""
        error = ChemblApiError("test error")
        assert isinstance(error, ExternalServiceError)

    def test_basic_initialization(self) -> None:
        """Test basic initialization with just message."""
        error = ChemblApiError("Connection failed")
        assert str(error) == "Connection failed"
        assert error.error_type == ErrorType.NETWORK_ERROR

    def test_initialization_with_status_code(self) -> None:
        """Test initialization with HTTP status code."""
        error = ChemblApiError("Not found", status_code=404)
        assert error.status_code == 404
        assert "Not found" in str(error)

    def test_initialization_with_entity_type(self) -> None:
        """Test initialization with entity type context."""
        error = ChemblApiError(
            "Failed to fetch",
            entity_type="activity",
            operation="fetch_batch",
        )
        assert error.entity_type == "activity"
        assert error.operation == "fetch_batch"

    def test_service_name_is_chembl(self) -> None:
        """Test that service name is always 'chembl'."""
        error = ChemblApiError("test")
        assert error.service_name == "chembl"


@pytest.mark.unit
class TestChemblRateLimitError:
    """Test ChemblRateLimitError exception."""

    def test_inherits_from_chembl_api_error(self) -> None:
        """Test inheritance chain."""
        error = ChemblRateLimitError()
        assert isinstance(error, ChemblApiError)
        assert isinstance(error, ExternalServiceError)

    def test_default_retry_after(self) -> None:
        """Test default retry_after value."""
        error = ChemblRateLimitError()
        assert error.retry_after == 60.0
        assert error.status_code == 429

    def test_custom_retry_after(self) -> None:
        """Test custom retry_after value."""
        error = ChemblRateLimitError(retry_after=120.0)
        assert error.retry_after == 120.0

    def test_error_type_is_rate_limit(self) -> None:
        """Test error type classification."""
        error = ChemblRateLimitError()
        assert error.error_type == ErrorType.RATE_LIMIT

    def test_message_contains_retry_info(self) -> None:
        """Test that message contains retry information."""
        error = ChemblRateLimitError(retry_after=30.0)
        assert "30" in str(error)
        assert "retry" in str(error).lower()


@pytest.mark.unit
class TestChemblServiceUnavailableError:
    """Test ChemblServiceUnavailableError exception."""

    def test_inherits_from_chembl_api_error(self) -> None:
        """Test inheritance chain."""
        error = ChemblServiceUnavailableError()
        assert isinstance(error, ChemblApiError)

    def test_default_message(self) -> None:
        """Test default error message."""
        error = ChemblServiceUnavailableError()
        assert "unavailable" in str(error).lower()

    def test_custom_message(self) -> None:
        """Test custom error message."""
        error = ChemblServiceUnavailableError(message="Server error")
        assert "Server error" in str(error)

    def test_with_status_code(self) -> None:
        """Test with HTTP status code."""
        error = ChemblServiceUnavailableError(
            message="Internal Server Error",
            status_code=500,
        )
        assert error.status_code == 500

    def test_error_type_is_timeout(self) -> None:
        """Test error type classification."""
        error = ChemblServiceUnavailableError()
        assert error.error_type == ErrorType.TIMEOUT


@pytest.mark.unit
class TestChemblAuthError:
    """Test ChemblAuthError exception."""

    def test_inherits_from_chembl_api_error(self) -> None:
        """Test inheritance chain."""
        error = ChemblAuthError()
        assert isinstance(error, ChemblApiError)

    def test_default_status_code_401(self) -> None:
        """Test default status code is 401."""
        error = ChemblAuthError()
        assert error.status_code == 401

    def test_custom_status_code_403(self) -> None:
        """Test custom status code 403."""
        error = ChemblAuthError(status_code=403)
        assert error.status_code == 403

    def test_error_type_is_auth_failure(self) -> None:
        """Test error type classification."""
        error = ChemblAuthError()
        assert error.error_type == ErrorType.AUTH_FAILURE

    def test_message_contains_status_code(self) -> None:
        """Test that message contains HTTP status code."""
        error = ChemblAuthError(status_code=403)
        assert "403" in str(error)
        assert "authentication" in str(error).lower()


@pytest.mark.unit
class TestExceptionModuleExports:
    """Test module exports and __all__."""

    def test_all_exports_are_available(self) -> None:
        """Test that all exports in __all__ are importable."""
        from bioetl.infrastructure.adapters.chembl import exceptions

        for name in exceptions.__all__:
            assert hasattr(exceptions, name)

    def test_all_contains_expected_exceptions(self) -> None:
        """Test that __all__ contains all expected exceptions."""
        from bioetl.infrastructure.adapters.chembl import exceptions

        expected = {
            "ChemblApiError",
            "ChemblAuthError",
            "ChemblRateLimitError",
            "ChemblServiceUnavailableError",
        }
        assert set(exceptions.__all__) == expected
