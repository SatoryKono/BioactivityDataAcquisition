"""Tests for unified adapter error handling.

Tests that AdapterErrorHandler provides consistent error classification,
logging, and exception wrapping across all adapters (RULES.md §4.1).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from bioetl.domain.exceptions import (
    AuthFailureError,
    NetworkError,
    RateLimitError,
    TimeoutError,
)
from bioetl.infrastructure.adapters.error_handling import (
    AdapterErrorHandler,
    ErrorCategory,
    classify_http_status,
    extract_retry_after,
)


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_critical_value(self):
        """Test CRITICAL category value."""
        assert ErrorCategory.CRITICAL.value == "CRITICAL"

    def test_recoverable_value(self):
        """Test RECOVERABLE category value."""
        assert ErrorCategory.RECOVERABLE.value == "RECOVERABLE"

    def test_data_quality_value(self):
        """Test DATA_QUALITY category value."""
        assert ErrorCategory.DATA_QUALITY.value == "DATA_QUALITY"


class TestClassifyHttpStatus:
    """Tests for HTTP status code classification."""

    @pytest.mark.parametrize(
        "status_code,expected_category",
        [
            # Critical errors (auth failures)
            (401, ErrorCategory.CRITICAL),
            (403, ErrorCategory.CRITICAL),
            # Recoverable errors (rate limit, server errors)
            (429, ErrorCategory.RECOVERABLE),
            (500, ErrorCategory.RECOVERABLE),
            (502, ErrorCategory.RECOVERABLE),
            (503, ErrorCategory.RECOVERABLE),
            (504, ErrorCategory.RECOVERABLE),
            # Data quality errors (client errors)
            (400, ErrorCategory.DATA_QUALITY),
            (404, ErrorCategory.DATA_QUALITY),
            (422, ErrorCategory.DATA_QUALITY),
        ],
    )
    def test_classify_http_status(
        self, status_code: int, expected_category: ErrorCategory
    ):
        """Test HTTP status code classification."""
        assert classify_http_status(status_code) == expected_category

    def test_unknown_5xx_is_recoverable(self):
        """Test that unknown 5xx codes are classified as RECOVERABLE."""
        assert classify_http_status(599) == ErrorCategory.RECOVERABLE

    def test_unknown_4xx_is_data_quality(self):
        """Test that unknown 4xx codes are classified as DATA_QUALITY."""
        assert classify_http_status(418) == ErrorCategory.DATA_QUALITY  # I'm a teapot


class TestExtractRetryAfter:
    """Tests for Retry-After header extraction."""

    def test_extract_numeric_retry_after(self):
        """Test extraction of numeric Retry-After value."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"Retry-After": "60"}
        assert extract_retry_after(response) == 60.0

    def test_extract_float_retry_after(self):
        """Test extraction of float Retry-After value."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"Retry-After": "30.5"}
        assert extract_retry_after(response) == 30.5

    def test_no_retry_after_header(self):
        """Test when Retry-After header is missing."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {}
        assert extract_retry_after(response) is None

    def test_invalid_retry_after_header(self):
        """Test when Retry-After header is not a number."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"}
        assert extract_retry_after(response) is None


class TestAdapterErrorHandler:
    """Tests for AdapterErrorHandler class."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        logger = MagicMock()
        return logger

    @pytest.fixture
    def mock_circuit_breaker(self):
        """Create a mock circuit breaker."""
        from bioetl.infrastructure.adapters.http.circuit_breaker import (
            CircuitBreaker,
            CircuitBreakerState,
        )

        cb = MagicMock(spec=CircuitBreaker)
        cb.get_state.return_value = CircuitBreakerState.CLOSED
        cb.get_failure_count.return_value = 0
        return cb

    @pytest.fixture
    def handler(self, mock_logger, mock_circuit_breaker):
        """Create an error handler for testing."""
        return AdapterErrorHandler(
            logger=mock_logger,
            provider="test_provider",
            circuit_breaker=mock_circuit_breaker,
        )

    def test_provider_property(self, handler):
        """Test provider property returns correct value."""
        assert handler.provider == "test_provider"

    def test_classify_error_with_domain_exception(self, handler):
        """Test error classification with domain exceptions."""
        from bioetl.domain.exceptions import RateLimitError

        error = RateLimitError(provider="test", retry_after=60.0)
        category = handler.classify_error(error)
        assert category == ErrorCategory.RECOVERABLE

    def test_classify_http_error(self, handler):
        """Test HTTP status code classification."""
        assert handler.classify_http_error(401) == ErrorCategory.CRITICAL
        assert handler.classify_http_error(429) == ErrorCategory.RECOVERABLE
        assert handler.classify_http_error(400) == ErrorCategory.DATA_QUALITY

    def test_should_retry_recoverable(self, handler):
        """Test that recoverable errors should be retried."""
        from bioetl.domain.exceptions import RateLimitError

        error = RateLimitError(provider="test", retry_after=60.0)
        assert handler.should_retry(error) is True

    def test_should_not_retry_critical(self, handler):
        """Test that critical errors should not be retried."""
        from bioetl.domain.exceptions import AuthFailureError

        error = AuthFailureError(provider="test", status_code=401)
        assert handler.should_retry(error) is False

    def test_log_error_includes_context(self, handler, mock_logger):
        """Test that log_error includes all context."""
        error = RuntimeError("Test error")
        handler.log_error("fetch", error, status_code=500, retry_count=2)

        # Verify logger was called
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]

        # Verify context fields
        assert call_kwargs["provider"] == "test_provider"
        assert call_kwargs["operation"] == "fetch"
        assert call_kwargs["status_code"] == 500
        assert call_kwargs["retry_count"] == 2
        assert "error_category" in call_kwargs
        assert "error_type" in call_kwargs

    def test_log_error_critical_uses_error_level(self, handler, mock_logger):
        """Test that critical errors are logged at error level."""
        error = AuthFailureError(provider="test", status_code=401)
        handler.log_error("auth", error)

        mock_logger.error.assert_called_once()

    def test_wrap_error_returns_domain_exception_unchanged(self, handler):
        """Test that domain exceptions are returned unchanged."""
        original = RateLimitError(provider="test", retry_after=60.0)
        wrapped = handler.wrap_error(original, "fetch")
        assert wrapped is original

    def test_wrap_error_401_returns_auth_failure(self, handler):
        """Test that 401 errors are wrapped as AuthFailureError."""
        error = RuntimeError("Unauthorized")
        wrapped = handler.wrap_error(error, "fetch", status_code=401)

        assert isinstance(wrapped, AuthFailureError)
        assert wrapped.provider == "test_provider"
        assert wrapped.status_code == 401

    def test_wrap_error_403_returns_auth_failure(self, handler):
        """Test that 403 errors are wrapped as AuthFailureError."""
        error = RuntimeError("Forbidden")
        wrapped = handler.wrap_error(error, "fetch", status_code=403)

        assert isinstance(wrapped, AuthFailureError)
        assert wrapped.status_code == 403

    def test_wrap_error_429_returns_rate_limit(self, handler):
        """Test that 429 errors are wrapped as RateLimitError."""
        error = RuntimeError("Too Many Requests")
        response = MagicMock(spec=httpx.Response)
        response.status_code = 429
        response.headers = {"Retry-After": "120"}

        wrapped = handler.wrap_error(error, "fetch", status_code=429, response=response)

        assert isinstance(wrapped, RateLimitError)
        assert wrapped.provider == "test_provider"
        assert wrapped.retry_after == 120.0

    def test_wrap_error_502_returns_timeout(self, handler):
        """Test that 502 errors are wrapped as TimeoutError."""
        error = RuntimeError("Bad Gateway")
        wrapped = handler.wrap_error(error, "fetch", status_code=502)

        assert isinstance(wrapped, TimeoutError)

    def test_wrap_error_504_returns_timeout(self, handler):
        """Test that 504 errors are wrapped as TimeoutError."""
        error = RuntimeError("Gateway Timeout")
        wrapped = handler.wrap_error(error, "fetch", status_code=504)

        assert isinstance(wrapped, TimeoutError)

    def test_wrap_error_500_returns_network_error(self, handler):
        """Test that 500 errors are wrapped as NetworkError."""
        error = RuntimeError("Internal Server Error")
        wrapped = handler.wrap_error(error, "fetch", status_code=500)

        assert isinstance(wrapped, NetworkError)

    def test_handle_error_raises_wrapped_exception(self, handler, mock_logger):
        """Test that handle_error logs and raises wrapped exception."""
        error = RuntimeError("Test error")

        with pytest.raises(NetworkError):
            handler.handle_error(error, "fetch", status_code=500)

        # Verify logging occurred
        mock_logger.warning.assert_called_once()

    def test_handle_error_with_response(self, handler, mock_logger):
        """Test handle_error extracts status_code from response."""
        error = RuntimeError("Unauthorized")
        response = MagicMock(spec=httpx.Response)
        response.status_code = 401

        with pytest.raises(AuthFailureError):
            handler.handle_error(error, "fetch", response=response)


class TestUnifiedErrorBehavior:
    """Tests for unified error behavior across adapters."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    def test_all_adapters_handle_401_the_same(self, mock_logger):
        """Test that 401 is handled consistently across providers."""
        providers = ["chembl", "uniprot", "pubchem", "pubmed"]

        for provider in providers:
            handler = AdapterErrorHandler(logger=mock_logger, provider=provider)
            error = RuntimeError("Unauthorized")
            wrapped = handler.wrap_error(error, "fetch", status_code=401)

            assert isinstance(wrapped, AuthFailureError), f"Failed for {provider}"
            assert wrapped.provider == provider

    def test_all_adapters_handle_429_the_same(self, mock_logger):
        """Test that 429 is handled consistently across providers."""
        providers = ["chembl", "uniprot", "pubchem", "pubmed"]

        for provider in providers:
            handler = AdapterErrorHandler(logger=mock_logger, provider=provider)
            error = RuntimeError("Rate limited")
            wrapped = handler.wrap_error(error, "fetch", status_code=429)

            assert isinstance(wrapped, RateLimitError), f"Failed for {provider}"
            assert wrapped.provider == provider

    def test_all_adapters_handle_5xx_the_same(self, mock_logger):
        """Test that 5xx errors are handled consistently across providers."""
        providers = ["chembl", "uniprot", "pubchem", "pubmed"]
        status_codes = [500, 502, 503, 504]

        for provider in providers:
            handler = AdapterErrorHandler(logger=mock_logger, provider=provider)

            for status_code in status_codes:
                error = RuntimeError(f"Server error {status_code}")
                wrapped = handler.wrap_error(error, "fetch", status_code=status_code)

                # 502 and 504 should be TimeoutError, others NetworkError
                if status_code in (502, 504):
                    assert isinstance(
                        wrapped, TimeoutError
                    ), f"Failed for {provider}/{status_code}"
                else:
                    assert isinstance(
                        wrapped, NetworkError
                    ), f"Failed for {provider}/{status_code}"

    def test_log_format_is_consistent(self, mock_logger):
        """Test that log format is consistent across all providers."""
        providers = ["chembl", "uniprot", "pubchem", "pubmed"]
        required_fields = {
            "provider",
            "operation",
            "error_category",
            "error_type",
            "error_message",
            "error_class",
        }

        for provider in providers:
            mock_logger.reset_mock()
            handler = AdapterErrorHandler(logger=mock_logger, provider=provider)
            error = RuntimeError("Test error")
            handler.log_error("fetch", error)

            # Get the logged kwargs
            call_kwargs = mock_logger.warning.call_args[1]

            # Verify all required fields are present
            for field in required_fields:
                assert field in call_kwargs, f"Missing {field} for {provider}"
