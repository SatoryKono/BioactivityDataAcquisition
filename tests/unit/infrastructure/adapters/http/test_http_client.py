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
        config = RetryConfig(base_delay=10.0, jitter=0.1)
        delays = [config.calculate_delay(0) for _ in range(10)]
        # With 10% jitter, delays should vary between 9 and 11
        assert not all(d == delays[0] for d in delays)  # Some variation expected


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
        retry_config=RetryConfig(max_attempts=2, jitter=0.0),
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
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_circuit_breaker.call.return_value = mock_response

        async with http_client:
            response = await http_client.get("https://api.example.com/data")

        assert response == mock_response

    @pytest.mark.asyncio
    async def test_get_with_params_and_headers(self, http_client, mock_circuit_breaker):
        """Test GET request with params and headers."""
        mock_response = MagicMock()
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
