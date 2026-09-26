# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for HTTP client retry mixin refactoring."""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from bioetl.domain.resilience import RetryConfig
import bioetl.infrastructure.adapters.http._client_retry_policy as retry_policy_module
import bioetl.infrastructure.adapters.http.client_retry_mixin as retry_mixin_module

from bioetl.infrastructure.adapters.http.client_retry_mixin import HTTPClientRetryMixin
from bioetl.infrastructure.adapters.http._client_retry_models import (
    _RetryRequestState,
    _RequestAttemptOutcome,
)


pytestmark = pytest.mark.unit


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("retry_after", "now", "expected_delay"),
    [
        ("7", datetime(2015, 10, 21, 7, 27, 55, tzinfo=UTC), 7.0),
        ("999999", datetime(2015, 10, 21, 7, 27, 55, tzinfo=UTC), 60.0),
        ("nan", datetime(2015, 10, 21, 7, 27, 55, tzinfo=UTC), 1.0),
        ("inf", datetime(2015, 10, 21, 7, 27, 55, tzinfo=UTC), 1.0),
        ("-1", datetime(2015, 10, 21, 7, 27, 55, tzinfo=UTC), 1.0),
        ("bad date", datetime(2015, 10, 21, 7, 27, 55, tzinfo=UTC), 1.0),
        ("", datetime(2015, 10, 21, 7, 27, 55, tzinfo=UTC), 1.0),
        (
            "Wed, 21 Oct 2015 07:27:00 GMT",
            datetime(2015, 10, 21, 7, 27, 55, tzinfo=UTC),
            0.0,
        ),
        (
            "Wed, 21 Oct 2099 07:28:00 GMT",
            datetime(2015, 10, 21, 7, 27, 55, tzinfo=UTC),
            60.0,
        ),
        (
            "Wed, 21 Oct 2015 07:28:00 GMT",
            datetime(2015, 10, 21, 7, 27, 55, tzinfo=UTC),
            5.0,
        ),
    ],
)
async def test_retry_after_supports_seconds_and_http_date_deterministically(
    monkeypatch: pytest.MonkeyPatch,
    retry_after: str,
    now: datetime,
    expected_delay: float,
) -> None:
    """Retry-After parsing uses a deterministic wall-clock seam."""
    mixin = HTTPClientRetryMixin()
    mixin.retry_config = RetryConfig(
        base_delay=1.0,
        max_delay=60.0,
        jitter_range=(0.0, 0.0),
    )
    sleep = AsyncMock()

    class _FrozenClock:
        def now(self) -> datetime:
            return now

    monkeypatch.setattr(retry_policy_module, "SystemClock", lambda: _FrozenClock())
    monkeypatch.setattr(retry_mixin_module.asyncio, "sleep", sleep)
    request = httpx.Request("GET", "https://api.test.example/paper/search")
    response = httpx.Response(
        429,
        request=request,
        headers={"Retry-After": retry_after},
    )

    delay = await mixin._handle_retry_delay(0, str(request.url), response)

    assert delay == pytest.approx(expected_delay)
    sleep.assert_awaited_once_with(expected_delay)
