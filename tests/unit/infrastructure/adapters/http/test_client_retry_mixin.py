"""Unit tests for HTTP client retry mixin refactoring."""

import pytest
from unittest.mock import MagicMock, AsyncMock
import httpx

from bioetl.infrastructure.adapters.http.client_retry_mixin import HTTPClientRetryMixin
from bioetl.infrastructure.adapters.http._client_retry_models import (
    _RetryRequestState,
    _RequestAttemptOutcome,
)


class TestHTTPClientRetryRefactoring:
    """Test suite for refactored HTTP client retry logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mixin = HTTPClientRetryMixin()
        self.mixin.retry_config = MagicMock()
        self.mixin.provider = "test_provider"
        self.mixin.run_id = "test_run_id"
        self.mixin.logger = MagicMock()
        self.mixin.rate_limiter = MagicMock()
        self.mixin.circuit_breaker = MagicMock()

        # Mock retry config methods
        self.mixin.retry_config.max_attempts = 3

    def test_should_continue_retry_on_success_response(self):
        """Test that successful response stops retry loop."""
        retry_state = _RetryRequestState()
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200

        result = self.mixin._should_continue_retry(response, retry_state)

        assert result is False  # Should not continue on success
        assert retry_state.status_code == 200

    def test_should_continue_retry_on_retryable_outcome(self):
        """Test that retryable outcome continues retry loop."""
        retry_state = _RetryRequestState()

        # Create a retryable outcome
        outcome = _RequestAttemptOutcome(
            should_retry=True, status_code=503, retries_increment=1, last_error=None
        )

        result = self.mixin._should_continue_retry(outcome, retry_state)

        assert result is True  # Should continue retry

    def test_should_continue_retry_on_non_retryable_outcome(self):
        """Test that non-retryable outcome stops retry loop."""
        retry_state = _RetryRequestState()

        # Create a non-retryable outcome
        outcome = _RequestAttemptOutcome(
            should_retry=False, status_code=404, retries_increment=0, last_error=None
        )

        result = self.mixin._should_continue_retry(outcome, retry_state)

        assert result is False  # Should not continue retry

    def test_should_continue_retry_edge_cases(self):
        """Test edge cases in retry continuation logic."""
        retry_state = _RetryRequestState()

        # Test with None result - should raise AttributeError when trying to access status_code
        with pytest.raises(AttributeError):
            self.mixin._should_continue_retry(None, retry_state)

    @pytest.mark.asyncio
    async def test_request_with_retry_integration(self):
        """Integration test for the full retry loop with proper mocking."""
        # This test focuses on the refactored _should_continue_retry method
        # and verifies it works correctly in the context of the full retry loop

        self.mixin._get_client = MagicMock()
        self.mixin._tracer = MagicMock()
        self.mixin._metrics = MagicMock()
        self.mixin.retry_config.max_attempts = 3

        # Mock client
        mock_client = MagicMock()
        self.mixin._get_client.return_value = mock_client

        # Create a successful response
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200

        # Mock _attempt_request to return successful response on first try
        self.mixin._attempt_request = AsyncMock(return_value=response)

        # Mock the tracer's start_as_current_span method
        mock_span = MagicMock()
        self.mixin._tracer.start_as_current_span.return_value.__aenter__.return_value = mock_span

        result = await self.mixin._request_with_retry("GET", "https://test.com")

        assert result == response
        assert result.status_code == 200
        # Verify that _should_continue_retry was called and worked correctly
        assert self.mixin._attempt_request.call_count == 1  # Only one attempt needed

    @pytest.mark.asyncio
    async def test_request_with_retry_exhausted(self):
        """Test that exhausted retries raise exception."""
        self.mixin._get_client = MagicMock()
        self.mixin._tracer = MagicMock()
        self.mixin._metrics = MagicMock()
        self.mixin.retry_config.max_attempts = 2

        # Mock client
        mock_client = MagicMock()
        self.mixin._get_client.return_value = mock_client

        # Mock _attempt_request to return non-retryable outcome
        outcome = _RequestAttemptOutcome(
            should_retry=False, status_code=429, retries_increment=0, last_error=None
        )
        self.mixin._attempt_request = AsyncMock(return_value=outcome)

        # Mock the tracer's start_as_current_span method
        mock_span = MagicMock()
        self.mixin._tracer.start_as_current_span.return_value.__aenter__.return_value = mock_span

        with pytest.raises(Exception, match="Exhausted"):
            await self.mixin._request_with_retry("GET", "https://test.com")
