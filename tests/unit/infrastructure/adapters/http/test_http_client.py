"""Unit tests for UnifiedHTTPClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from bioetl.domain.exceptions import CircuitBreakerOpenError, RetryExhaustedError
from bioetl.infrastructure.adapters.http.client import (
    RetryConfig,
    UnifiedHTTPClient,
    _is_retryable_error,
    _is_retryable_status,
)


@pytest.mark.unit
class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.multiplier == 2.0
        assert config.jitter == 0.1

    def test_calculate_delay_first_attempt(self):
        """Test delay calculation for first attempt."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, jitter=0.0)
        delay = config.calculate_delay(0)
        assert delay == 1.0

    def test_calculate_delay_second_attempt(self):
        """Test delay calculation for second attempt."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, jitter=0.0)
        delay = config.calculate_delay(1)
        assert delay == 2.0

    def test_calculate_delay_third_attempt(self):
        """Test delay calculation for third attempt."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, jitter=0.0)
        delay = config.calculate_delay(2)
        assert delay == 4.0

    def test_calculate_delay_respects_max_delay(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(
            base_delay=10.0, multiplier=2.0, max_delay=15.0, jitter=0.0
        )
        delay = config.calculate_delay(5)  # Would be 320 without cap
        assert delay == 15.0

    def test_calculate_delay_with_jitter(self):
        """Test that jitter adds randomness."""
        config = RetryConfig(base_delay=10.0, jitter=0.1, deterministic=False)
        delays = [config.calculate_delay(0) for _ in range(10)]
        # With 10% jitter, delays should vary between 9 and 11
        assert not all(d == delays[0] for d in delays)  # Some variation expected

    def test_deterministic_jitter_same_input_same_output(self):
        """Test deterministic mode produces same delay for same inputs."""
        config = RetryConfig(
            base_delay=10.0,
            jitter=0.1,
            deterministic=True,
            jitter_seed=42,
        )
        url = "https://api.example.com/data"

        # Same inputs should produce identical delays
        delay1 = config.calculate_delay(attempt=0, url=url)
        delay2 = config.calculate_delay(attempt=0, url=url)
        delay3 = config.calculate_delay(attempt=0, url=url)

        assert delay1 == delay2 == delay3

        # Different attempt numbers should also be deterministic
        delay_a1 = config.calculate_delay(attempt=1, url=url)
        delay_a1_again = config.calculate_delay(attempt=1, url=url)
        assert delay_a1 == delay_a1_again

    def test_deterministic_jitter_different_urls_different_output(self):
        """Test deterministic mode produces different delays for different URLs."""
        config = RetryConfig(
            base_delay=10.0,
            jitter=0.1,
            deterministic=True,
            jitter_seed=42,
        )

        delay1 = config.calculate_delay(attempt=0, url="https://api.example.com/data1")
        delay2 = config.calculate_delay(attempt=0, url="https://api.example.com/data2")

        # Different URLs should produce different jitter values
        assert delay1 != delay2

        # Both should still be within jitter range (9.0 to 11.0)
        assert 9.0 <= delay1 <= 11.0
        assert 9.0 <= delay2 <= 11.0

    def test_non_deterministic_mode_uses_random(self):
        """Test non-deterministic mode produces varying delays."""
        config = RetryConfig(
            base_delay=10.0,
            jitter=0.1,
            deterministic=False,  # Explicit non-deterministic
        )
        url = "https://api.example.com/data"

        # Collect multiple delay values
        delays = [config.calculate_delay(attempt=0, url=url) for _ in range(20)]

        # With random jitter, not all delays should be identical
        # (extremely unlikely for 20 random values to be the same)
        unique_delays = set(delays)
        assert len(unique_delays) > 1, "Random jitter should produce varying delays"

        # All delays should still be within jitter range
        for delay in delays:
            assert 9.0 <= delay <= 11.0

    def test_deterministic_jitter_cross_process_stability(self):
        """Test deterministic jitter produces stable values across processes.

        This test verifies that the jitter calculation uses MD5 (not Python's
        hash()) which is stable across different Python processes. Python's
        built-in hash() uses PYTHONHASHSEED and produces different values in
        different processes.

        The expected values are pre-computed using MD5 and will remain constant
        regardless of which Python process runs this test.
        """
        import hashlib

        config = RetryConfig(
            base_delay=10.0,
            jitter=0.1,
            deterministic=True,
            jitter_seed=42,
        )
        url = "https://api.example.com/test"

        # Compute expected delay using MD5 directly (cross-process stable)
        hash_input = f"0:{url}:42"
        digest = hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()
        jitter_factor = int(digest[:8], 16) / 0xFFFFFFFF
        base_delay = 10.0
        jitter_range = base_delay * 0.1
        expected_delay = base_delay + jitter_range * (jitter_factor * 2 - 1)

        # Verify implementation matches our expectation
        actual_delay = config.calculate_delay(attempt=0, url=url)

        assert actual_delay == expected_delay, (
            f"Jitter calculation mismatch. Expected {expected_delay}, got {actual_delay}. "
            "This may indicate the implementation uses Python's hash() instead of MD5."
        )

        # Also verify the value is deterministic (same value on repeated calls)
        assert config.calculate_delay(attempt=0, url=url) == expected_delay
        assert config.calculate_delay(attempt=0, url=url) == expected_delay

    def test_deterministic_jitter_known_values(self):
        """Test deterministic jitter produces known stable values.

        These values are pre-computed and serve as a regression test.
        If this test fails, it means the jitter algorithm has changed.
        """
        config = RetryConfig(
            base_delay=1.0,
            jitter=0.5,
            deterministic=True,
            jitter_seed=123,
        )

        # Pre-computed expected values using MD5
        # These should remain constant across all Python processes
        test_cases = [
            (0, "https://example.com/a", 0.6598315358068402),
            (1, "https://example.com/a", 1.2365159788719648),
            (0, "https://example.com/b", 1.0166028722926517),
            (2, "https://example.com/c", 3.1987770072181654),
        ]

        for attempt, url, expected in test_cases:
            actual = config.calculate_delay(attempt=attempt, url=url)
            assert abs(actual - expected) < 1e-10, (
                f"Delay mismatch for attempt={attempt}, url={url}. "
                f"Expected {expected}, got {actual}"
            )


@pytest.mark.unit
class TestIsRetryableStatus:
    """Tests for _is_retryable_status function."""

    @pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
    def test_retryable_statuses(self, status):
        """Test that retryable statuses return True."""
        assert _is_retryable_status(status) is True

    @pytest.mark.parametrize("status", [200, 201, 400, 401, 403, 404, 405])
    def test_non_retryable_statuses(self, status):
        """Test that non-retryable statuses return False."""
        assert _is_retryable_status(status) is False


@pytest.mark.unit
class TestIsRetryableError:
    """Tests for _is_retryable_error function."""

    def test_connect_error_is_retryable(self):
        """Test ConnectError is retryable."""
        exc = httpx.ConnectError("Connection failed")
        assert _is_retryable_error(exc) is True

    def test_connect_timeout_is_retryable(self):
        """Test ConnectTimeout is retryable."""
        exc = httpx.ConnectTimeout("Connection timed out")
        assert _is_retryable_error(exc) is True

    def test_read_timeout_is_retryable(self):
        """Test ReadTimeout is retryable."""
        exc = httpx.ReadTimeout("Read timed out")
        assert _is_retryable_error(exc) is True

    def test_http_status_error_with_retryable_code(self):
        """Test HTTPStatusError with retryable status code."""
        response = MagicMock()
        response.status_code = 503
        exc = httpx.HTTPStatusError(
            "Service Unavailable", request=MagicMock(), response=response
        )
        assert _is_retryable_error(exc) is True

    def test_http_status_error_with_non_retryable_code(self):
        """Test HTTPStatusError with non-retryable status code."""
        response = MagicMock()
        response.status_code = 404
        exc = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=response)
        assert _is_retryable_error(exc) is False

    def test_other_exception_not_retryable(self):
        """Test other exceptions are not retryable."""
        exc = ValueError("Some error")
        assert _is_retryable_error(exc) is False


@pytest.fixture
def mock_rate_limiter():
    """Create mock rate limiter."""
    limiter = MagicMock()
    limiter.acquire = AsyncMock()
    return limiter


@pytest.fixture
def mock_circuit_breaker():
    """Create mock circuit breaker."""
    cb = MagicMock()
    cb.call = AsyncMock()
    return cb


@pytest.fixture
def http_client(mock_rate_limiter, mock_circuit_breaker):
    """Create UnifiedHTTPClient instance."""
    return UnifiedHTTPClient(
        rate_limiter=mock_rate_limiter,
        circuit_breaker=mock_circuit_breaker,
        retry_policy=RetryConfig(max_attempts=2, jitter=0.0),
        timeout=10.0,
    )


@pytest.mark.unit
class TestUnifiedHTTPClientInit:
    """Tests for UnifiedHTTPClient initialization."""

    def test_init_with_defaults(self, mock_rate_limiter, mock_circuit_breaker):
        """Test initialization with default values."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
        )
        assert client.timeout == 30.0
        assert client.run_id is None
        assert client.user_agent == "BioETL/5.0.0"
        assert client.contact_email is None
        assert client._client is None

    def test_init_with_run_id(self, mock_rate_limiter, mock_circuit_breaker):
        """Test initialization with run_id."""
        run_id = uuid4()
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
            run_id=run_id,
        )
        assert client.run_id == run_id

    def test_init_with_custom_user_agent(self, mock_rate_limiter, mock_circuit_breaker):
        """Test initialization with custom user_agent."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
            user_agent="CustomApp/1.0.0",
        )
        assert client.user_agent == "CustomApp/1.0.0"

    def test_init_with_contact_email(self, mock_rate_limiter, mock_circuit_breaker):
        """Test initialization with contact_email."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
            contact_email="admin@example.com",
        )
        assert client.contact_email == "admin@example.com"


@pytest.mark.unit
class TestUnifiedHTTPClientContextManager:
    """Tests for context manager behavior."""

    @pytest.mark.asyncio
    async def test_aenter_creates_client(self, http_client):
        """Test __aenter__ creates httpx client."""
        async with http_client as client:
            assert client._client is not None
            assert isinstance(client._client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_aexit_closes_client(self, http_client):
        """Test __aexit__ closes httpx client."""
        async with http_client:
            pass
        assert http_client._client is None

    @pytest.mark.asyncio
    async def test_aenter_with_run_id_sets_header(
        self, mock_rate_limiter, mock_circuit_breaker
    ):
        """Test __aenter__ sets correlation ID header when run_id provided."""
        run_id = uuid4()
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
            run_id=run_id,
        )

        async with client:
            headers = client._client.headers
            assert "X-Correlation-ID" in headers
            assert headers["X-Correlation-ID"] == str(run_id)

    @pytest.mark.asyncio
    async def test_aenter_sets_default_user_agent(
        self, mock_rate_limiter, mock_circuit_breaker
    ):
        """Test __aenter__ sets default User-Agent header."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
        )

        async with client:
            headers = client._client.headers
            assert headers["User-Agent"] == "BioETL/5.0.0"

    @pytest.mark.asyncio
    async def test_aenter_sets_custom_user_agent(
        self, mock_rate_limiter, mock_circuit_breaker
    ):
        """Test __aenter__ sets custom User-Agent header."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
            user_agent="CustomApp/2.0.0",
        )

        async with client:
            headers = client._client.headers
            assert headers["User-Agent"] == "CustomApp/2.0.0"

    @pytest.mark.asyncio
    async def test_aenter_appends_contact_email_to_user_agent(
        self, mock_rate_limiter, mock_circuit_breaker
    ):
        """Test __aenter__ appends contact_email to User-Agent when provided."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
            contact_email="support@example.com",
        )

        async with client:
            headers = client._client.headers
            assert headers["User-Agent"] == "BioETL/5.0.0 (support@example.com)"

    @pytest.mark.asyncio
    async def test_aenter_with_custom_user_agent_and_email(
        self, mock_rate_limiter, mock_circuit_breaker
    ):
        """Test __aenter__ with both custom user_agent and contact_email."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
            user_agent="MyApp/3.0.0",
            contact_email="admin@myapp.com",
        )

        async with client:
            headers = client._client.headers
            assert headers["User-Agent"] == "MyApp/3.0.0 (admin@myapp.com)"


@pytest.mark.unit
class TestUnifiedHTTPClientGetClient:
    """Tests for _get_client method."""

    def test_get_client_raises_when_not_in_context(self, http_client):
        """Test _get_client raises RuntimeError outside context."""
        with pytest.raises(RuntimeError, match="must be used within async context"):
            http_client._get_client()

    @pytest.mark.asyncio
    async def test_get_client_returns_client_in_context(self, http_client):
        """Test _get_client returns client within context."""
        async with http_client:
            client = http_client._get_client()
            assert client is not None
            assert isinstance(client, httpx.AsyncClient)


@pytest.mark.unit
class TestUnifiedHTTPClientHandleRetryDelay:
    """Tests for _handle_retry_delay method."""

    @pytest.mark.asyncio
    async def test_handle_retry_delay_uses_calculated_delay(self, http_client):
        """Test _handle_retry_delay uses calculated delay."""
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await http_client._handle_retry_delay(attempt=0)
            mock_sleep.assert_called_once()
            # First attempt with base_delay=1.0
            assert mock_sleep.call_args[0][0] == 1.0

    @pytest.mark.asyncio
    async def test_handle_retry_delay_respects_retry_after_header(self, http_client):
        """Test _handle_retry_delay uses Retry-After header if present."""
        response = MagicMock()
        response.headers = {"Retry-After": "5"}

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await http_client._handle_retry_delay(attempt=0, response=response)
            mock_sleep.assert_called_once_with(5.0)


@pytest.mark.unit
class TestUnifiedHTTPClientRequestMethods:
    """Tests for GET, POST, HEAD request methods."""

    @pytest.mark.asyncio
    async def test_get_success(self, http_client, mock_circuit_breaker):
        """Test successful GET request."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_circuit_breaker.call.return_value = mock_response

        async with http_client:
            response = await http_client.get("https://api.example.com/data")

        assert response == mock_response

    @pytest.mark.asyncio
    async def test_get_with_params_and_headers(self, http_client, mock_circuit_breaker):
        """Test GET request with params and headers."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_circuit_breaker.call.return_value = mock_response

        async with http_client:
            await http_client.get(
                "https://api.example.com/data",
                params={"page": 1},
                headers={"Accept": "application/json"},
            )

        mock_circuit_breaker.call.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_with_json(self, http_client, mock_circuit_breaker):
        """Test POST request with JSON body."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.raise_for_status = MagicMock()
        mock_circuit_breaker.call.return_value = mock_response

        async with http_client:
            response = await http_client.post(
                "https://api.example.com/data",
                json={"name": "test"},
            )

        assert response == mock_response

    @pytest.mark.asyncio
    async def test_head_request(self, http_client, mock_circuit_breaker):
        """Test HEAD request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_circuit_breaker.call.return_value = mock_response

        async with http_client:
            response = await http_client.head("https://api.example.com/health")

        assert response == mock_response

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_error_propagates(
        self, http_client, mock_circuit_breaker
    ):
        """Test CircuitBreakerOpenError is not retried."""
        mock_circuit_breaker.call.side_effect = CircuitBreakerOpenError(
            "chembl", "Circuit is open"
        )

        async with http_client:
            with pytest.raises(CircuitBreakerOpenError):
                await http_client.get("https://api.example.com/data")

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_error(
        self, http_client, mock_circuit_breaker
    ):
        """Test RetryExhaustedError after all retries."""
        mock_circuit_breaker.call.side_effect = httpx.ConnectError("Connection failed")

        async with http_client:
            with pytest.raises(RetryExhaustedError):
                await http_client.get("https://api.example.com/data")

        # Should have tried max_attempts times
        assert mock_circuit_breaker.call.call_count == 2

    @pytest.mark.asyncio
    async def test_retryable_status_triggers_retry(
        self, http_client, mock_circuit_breaker
    ):
        """Test retryable status code triggers retry."""
        mock_response_503 = MagicMock()
        mock_response_503.status_code = 503
        mock_response_503.headers = {}

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.raise_for_status = MagicMock()

        mock_circuit_breaker.call.side_effect = [mock_response_503, mock_response_200]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            async with http_client:
                response = await http_client.get("https://api.example.com/data")

        assert response == mock_response_200
        assert mock_circuit_breaker.call.call_count == 2


@pytest.mark.unit
class TestUnifiedHTTPClientObservability:
    """Tests for observability features (Phase 1 refactoring)."""

    @pytest.fixture
    def mock_tracer(self):
        """Create mock tracer with span tracking."""
        span = MagicMock()
        span.__enter__ = MagicMock(return_value=span)
        span.__exit__ = MagicMock(return_value=None)

        otel_tracer = MagicMock()
        otel_tracer.start_as_current_span = MagicMock(return_value=span)

        tracer = MagicMock()
        tracer.get_tracer = MagicMock(return_value=otel_tracer)

        return tracer, span

    @pytest.fixture
    def mock_metrics(self):
        """Create mock metrics port."""
        metrics = MagicMock()
        metrics.observe_histogram = MagicMock()
        metrics.increment_counter = MagicMock()
        return metrics

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger port."""
        logger = MagicMock()
        logger.debug = MagicMock()
        logger.warning = MagicMock()
        return logger

    @pytest.fixture
    def http_client_with_observability(
        self, mock_rate_limiter, mock_circuit_breaker, mock_tracer, mock_metrics, mock_logger
    ):
        """Create client with all observability components."""
        tracer, _ = mock_tracer
        return UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
            retry_policy=RetryConfig(max_attempts=2, jitter=0.0),
            timeout=10.0,
            provider="test_provider",
            tracer=tracer,
            metrics=mock_metrics,
            logger=mock_logger,
        )

    @pytest.mark.asyncio
    async def test_successful_request_creates_span(
        self, http_client_with_observability, mock_circuit_breaker, mock_tracer
    ):
        """Test successful request creates tracing span with correct attributes."""
        tracer, span = mock_tracer

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_circuit_breaker.call.return_value = mock_response

        async with http_client_with_observability:
            await http_client_with_observability.get("https://api.example.com/data")

        # Verify span was created
        tracer.get_tracer.assert_called_once_with("bioetl.http")
        otel_tracer = tracer.get_tracer.return_value
        otel_tracer.start_as_current_span.assert_called_once()

        # Check span name and attributes
        call_args = otel_tracer.start_as_current_span.call_args
        assert call_args[0][0] == "http.get"
        attrs = call_args[1]["attributes"]
        assert attrs["http.method"] == "GET"
        assert attrs["http.url"] == "https://api.example.com/data"
        assert attrs["bioetl.provider"] == "test_provider"

        # Verify span was closed
        span.__enter__.assert_called_once()
        span.__exit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_request_records_metrics(
        self, http_client_with_observability, mock_circuit_breaker, mock_metrics
    ):
        """Test successful request records duration histogram."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_circuit_breaker.call.return_value = mock_response

        async with http_client_with_observability:
            await http_client_with_observability.get("https://api.example.com/data")

        # Verify histogram was observed
        mock_metrics.observe_histogram.assert_called_once()
        call_args = mock_metrics.observe_histogram.call_args
        assert call_args[0][0] == "http_request_duration_seconds"
        assert call_args[0][1] > 0  # duration
        labels = call_args[0][2]
        assert labels["provider"] == "test_provider"
        assert labels["method"] == "GET"
        assert labels["status"] == "200"

    @pytest.mark.asyncio
    async def test_retry_records_retry_counter(
        self, http_client_with_observability, mock_circuit_breaker, mock_metrics
    ):
        """Test retry increments retry counter."""
        mock_response_503 = MagicMock()
        mock_response_503.status_code = 503
        mock_response_503.headers = {}

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.raise_for_status = MagicMock()

        mock_circuit_breaker.call.side_effect = [mock_response_503, mock_response_200]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            async with http_client_with_observability:
                await http_client_with_observability.get("https://api.example.com/data")

        # Verify retry counter was incremented
        counter_calls = [
            c for c in mock_metrics.increment_counter.call_args_list
            if c[0][0] == "http_retries_total"
        ]
        assert len(counter_calls) == 1
        assert counter_calls[0][0][1] == 1  # 1 retry

    @pytest.mark.asyncio
    async def test_error_records_error_counter(
        self, http_client_with_observability, mock_circuit_breaker, mock_metrics
    ):
        """Test error increments error counter."""
        mock_circuit_breaker.call.side_effect = httpx.ConnectError("Connection failed")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            async with http_client_with_observability:
                with pytest.raises(RetryExhaustedError):
                    await http_client_with_observability.get("https://api.example.com/data")

        # Verify error counter was incremented
        error_calls = [
            c for c in mock_metrics.increment_counter.call_args_list
            if c[0][0] == "http_request_errors_total"
        ]
        assert len(error_calls) == 1
        labels = error_calls[0][0][2]
        assert labels["provider"] == "test_provider"
        assert labels["error_type"] == "ConnectError"

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_logs_warning(
        self, http_client_with_observability, mock_circuit_breaker, mock_logger
    ):
        """Test circuit breaker open logs warning."""
        mock_circuit_breaker.call.side_effect = CircuitBreakerOpenError(
            "test_provider", "Circuit is open"
        )

        async with http_client_with_observability:
            with pytest.raises(CircuitBreakerOpenError):
                await http_client_with_observability.get("https://api.example.com/data")

        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "http_circuit_breaker_open"
        assert call_args[1]["provider"] == "test_provider"

    @pytest.mark.asyncio
    async def test_retry_logs_debug(
        self, http_client_with_observability, mock_circuit_breaker, mock_logger
    ):
        """Test retry logs debug message."""
        mock_response_503 = MagicMock()
        mock_response_503.status_code = 503
        mock_response_503.headers = {}

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.raise_for_status = MagicMock()

        mock_circuit_breaker.call.side_effect = [mock_response_503, mock_response_200]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            async with http_client_with_observability:
                await http_client_with_observability.get("https://api.example.com/data")

        # Verify debug was logged for retry
        mock_logger.debug.assert_called()
        call_args = mock_logger.debug.call_args
        assert call_args[0][0] == "http_retry"

    def test_default_observability_uses_noop(self, mock_rate_limiter, mock_circuit_breaker):
        """Test client uses NoOp implementations when observability not provided."""
        from bioetl.domain.ports import NoOpMetrics, NoOpTracing

        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
        )

        assert isinstance(client._tracer, NoOpTracing)
        assert isinstance(client._metrics, NoOpMetrics)

    def test_provider_attribute_set(self, mock_rate_limiter, mock_circuit_breaker):
        """Test provider attribute is set correctly."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
            provider="chembl",
        )
        assert client.provider == "chembl"
