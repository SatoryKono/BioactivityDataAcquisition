"""Unit tests for UnifiedHTTPClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from bioetl.domain.exceptions import CircuitBreakerOpenError, RetryExhaustedError
from bioetl.domain.resilience import RetryConfig
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


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
        assert config.jitter_range == (0.1, 0.5)
        assert config.retryable_statuses == frozenset({429, 500, 502, 503, 504})
        assert ConnectionError in config.retryable_exceptions
        assert TimeoutError in config.retryable_exceptions

    def test_calculate_delay_first_attempt(self):
        """Test delay calculation for first attempt (no jitter)."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, jitter_range=(0.0, 0.0))
        delay = config.calculate_delay(0)
        assert delay == 1.0

    def test_calculate_delay_second_attempt(self):
        """Test delay calculation for second attempt (no jitter)."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, jitter_range=(0.0, 0.0))
        delay = config.calculate_delay(1)
        assert delay == 2.0

    def test_calculate_delay_third_attempt(self):
        """Test delay calculation for third attempt (no jitter)."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, jitter_range=(0.0, 0.0))
        delay = config.calculate_delay(2)
        assert delay == 4.0

    def test_calculate_delay_respects_max_delay(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(
            base_delay=10.0, multiplier=2.0, max_delay=15.0, jitter_range=(0.0, 0.0)
        )
        delay = config.calculate_delay(5)  # Would be 320 without cap
        assert delay == 15.0

    def test_is_retryable_status(self):
        """Test is_retryable_status method."""
        config = RetryConfig()
        assert config.is_retryable_status(429)
        assert config.is_retryable_status(500)  # Internal Server Error is retryable
        assert config.is_retryable_status(502)
        assert config.is_retryable_status(503)
        assert config.is_retryable_status(504)
        assert not config.is_retryable_status(200)
        assert not config.is_retryable_status(400)
        assert not config.is_retryable_status(401)

    def test_is_retryable_exception(self):
        """Test is_retryable_exception method."""
        config = RetryConfig()
        assert config.is_retryable_exception(ConnectionError("test"))
        assert config.is_retryable_exception(TimeoutError("test"))
        assert not config.is_retryable_exception(ValueError("test"))

    def test_custom_retryable_statuses(self):
        """Test custom retryable status codes."""
        config = RetryConfig(retryable_statuses=frozenset({500, 502}))
        assert config.is_retryable_status(500)
        assert config.is_retryable_status(502)
        assert not config.is_retryable_status(429)  # No longer in list

    def test_jitter_same_input_same_output(self):
        """Test jitter produces same delay for same inputs (deterministic)."""
        config = RetryConfig(
            base_delay=10.0,
            jitter_range=(0.1, 0.3),
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

    def test_jitter_different_urls_different_output(self):
        """Test jitter produces different delays for different URLs."""
        config = RetryConfig(
            base_delay=10.0,
            jitter_range=(0.1, 0.2),
            jitter_seed=42,
        )

        delay1 = config.calculate_delay(attempt=0, url="https://api.example.com/data1")
        delay2 = config.calculate_delay(attempt=0, url="https://api.example.com/data2")

        # Different URLs should produce different jitter values
        assert delay1 != delay2

        # Both should still be within jitter range: base * (1 + jitter)
        # With jitter_range=(0.1, 0.2), delay should be between 11.0 and 12.0
        assert 11.0 <= delay1 <= 12.0
        assert 11.0 <= delay2 <= 12.0

    def test_jitter_cross_process_stability(self):
        """Test deterministic jitter produces stable values across processes.

        This test verifies that the jitter calculation uses MD5 (not Python's
        hash()) which is stable across different Python processes.
        """
        import hashlib

        config = RetryConfig(
            base_delay=10.0,
            jitter_range=(0.1, 0.2),
            jitter_seed=42,
        )
        url = "https://api.example.com/test"

        # Compute expected delay using MD5 directly (cross-process stable)
        hash_input = f"0:{url}:42"
        digest = hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()
        jitter_factor = int(digest[:8], 16) / 0xFFFFFFFF

        base_delay = 10.0
        jitter_min, jitter_max = 0.1, 0.2
        jitter_span = jitter_max - jitter_min
        jitter_amount = jitter_min + (jitter_span * jitter_factor)
        expected_delay = min(base_delay * (1 + jitter_amount), config.max_delay)

        # Verify implementation matches our expectation
        actual_delay = config.calculate_delay(attempt=0, url=url)

        assert actual_delay == expected_delay, (
            f"Jitter calculation mismatch. Expected {expected_delay}, got {actual_delay}. "
            "This may indicate the implementation uses Python's hash() instead of MD5."
        )

        # Also verify the value is deterministic (same value on repeated calls)
        assert config.calculate_delay(attempt=0, url=url) == expected_delay
        assert config.calculate_delay(attempt=0, url=url) == expected_delay

    def test_is_last_attempt(self):
        """Test is_last_attempt method."""
        config = RetryConfig(max_attempts=3)
        assert not config.is_last_attempt(0)
        assert not config.is_last_attempt(1)
        assert config.is_last_attempt(2)
        assert config.is_last_attempt(3)  # Beyond last


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
        retry_config=RetryConfig(max_attempts=2, jitter_range=(0.0, 0.0)),
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
        mock_response = MagicMock(spec=httpx.Response)
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
        mock_response = MagicMock(spec=httpx.Response)
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
        mock_response_503 = MagicMock(spec=httpx.Response)
        mock_response_503.status_code = 503
        mock_response_503.headers = {}

        mock_response_200 = MagicMock(spec=httpx.Response)
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
        self,
        mock_rate_limiter,
        mock_circuit_breaker,
        mock_tracer,
        mock_metrics,
        mock_logger,
    ):
        """Create client with all observability components."""
        tracer, _ = mock_tracer
        return UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
            retry_config=RetryConfig(max_attempts=2, jitter_range=(0.0, 0.0)),
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

        mock_response = MagicMock(spec=httpx.Response)
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
        mock_response = MagicMock(spec=httpx.Response)
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
        mock_response_503 = MagicMock(spec=httpx.Response)
        mock_response_503.status_code = 503
        mock_response_503.headers = {}

        mock_response_200 = MagicMock(spec=httpx.Response)
        mock_response_200.status_code = 200
        mock_response_200.raise_for_status = MagicMock()

        mock_circuit_breaker.call.side_effect = [mock_response_503, mock_response_200]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            async with http_client_with_observability:
                await http_client_with_observability.get("https://api.example.com/data")

        # Verify retry counter was incremented
        counter_calls = [
            c
            for c in mock_metrics.increment_counter.call_args_list
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
                    await http_client_with_observability.get(
                        "https://api.example.com/data"
                    )

        # Verify error counter was incremented
        error_calls = [
            c
            for c in mock_metrics.increment_counter.call_args_list
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
    async def test_retry_logs_warning(
        self, http_client_with_observability, mock_circuit_breaker, mock_logger
    ):
        """Test retry logs warning message."""
        mock_response_503 = MagicMock(spec=httpx.Response)
        mock_response_503.status_code = 503
        mock_response_503.headers = {}

        mock_response_200 = MagicMock(spec=httpx.Response)
        mock_response_200.status_code = 200
        mock_response_200.raise_for_status = MagicMock()

        mock_circuit_breaker.call.side_effect = [mock_response_503, mock_response_200]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            async with http_client_with_observability:
                await http_client_with_observability.get("https://api.example.com/data")

        # Verify warning was logged for retry (not debug - retries are notable events)
        # Check that logger.warning was called at least once for retry
        mock_logger.warning.assert_called()
        call_args_list = mock_logger.warning.call_args_list
        retry_calls = [c for c in call_args_list if c.args and "Retry" in c.args[0]]
        assert len(retry_calls) >= 1, (
            f"Expected at least 1 retry warning call, got {len(retry_calls)}. "
            f"All warning calls: {call_args_list}"
        )
        # Verify retry call contains expected fields
        retry_call = retry_calls[0]
        assert "attempt" in retry_call.kwargs
        assert retry_call.kwargs["attempt"] == 1

    def test_default_observability_uses_noop(
        self, mock_rate_limiter, mock_circuit_breaker
    ):
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
