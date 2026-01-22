"""Unit tests for UnifiedHTTPClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


@pytest.fixture
def mock_rate_limiter():
    """Create mock rate limiter."""
    limiter = MagicMock()
    limiter.acquire = AsyncMock()
    return limiter


@pytest.fixture
def http_client(mock_rate_limiter):
    """Create UnifiedHTTPClient instance."""
    return UnifiedHTTPClient(
        rate_limiter=mock_rate_limiter,
        timeout=10.0,
    )


@pytest.mark.unit
class TestUnifiedHTTPClientInit:
    """Tests for UnifiedHTTPClient initialization."""

    def test_init_with_defaults(self, mock_rate_limiter):
        """Test initialization with default values."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
        )
        assert client.timeout == 30.0
        assert client.run_id is None
        assert client.user_agent == "BioETL/5.0.0"
        assert client.contact_email is None
        assert client._client is None

    def test_init_with_run_id(self, mock_rate_limiter):
        """Test initialization with run_id."""
        run_id = uuid4()
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            run_id=run_id,
        )
        assert client.run_id == run_id

    def test_init_with_custom_user_agent(self, mock_rate_limiter):
        """Test initialization with custom user_agent."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            user_agent="CustomApp/1.0.0",
        )
        assert client.user_agent == "CustomApp/1.0.0"

    def test_init_with_contact_email(self, mock_rate_limiter):
        """Test initialization with contact_email."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
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
        self, mock_rate_limiter
    ):
        """Test __aenter__ sets correlation ID header when run_id provided."""
        run_id = uuid4()
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            run_id=run_id,
        )

        async with client:
            headers = client._client.headers
            assert "X-Correlation-ID" in headers
            assert headers["X-Correlation-ID"] == str(run_id)

    @pytest.mark.asyncio
    async def test_aenter_sets_default_user_agent(
        self, mock_rate_limiter
    ):
        """Test __aenter__ sets default User-Agent header."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
        )

        async with client:
            headers = client._client.headers
            assert headers["User-Agent"] == "BioETL/5.0.0"

    @pytest.mark.asyncio
    async def test_aenter_sets_custom_user_agent(
        self, mock_rate_limiter
    ):
        """Test __aenter__ sets custom User-Agent header."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            user_agent="CustomApp/2.0.0",
        )

        async with client:
            headers = client._client.headers
            assert headers["User-Agent"] == "CustomApp/2.0.0"

    @pytest.mark.asyncio
    async def test_aenter_appends_contact_email_to_user_agent(
        self, mock_rate_limiter
    ):
        """Test __aenter__ appends contact_email to User-Agent when provided."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            contact_email="support@example.com",
        )

        async with client:
            headers = client._client.headers
            assert headers["User-Agent"] == "BioETL/5.0.0 (support@example.com)"

    @pytest.mark.asyncio
    async def test_aenter_with_custom_user_agent_and_email(
        self, mock_rate_limiter
    ):
        """Test __aenter__ with both custom user_agent and contact_email."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
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
class TestUnifiedHTTPClientRequestMethods:
    """Tests for GET, POST, HEAD request methods."""

    @pytest.mark.asyncio
    async def test_get_success(self, http_client):
        """Test successful GET request."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        async with http_client:
            # Mock the internal client's request method
            http_client._client.request = AsyncMock(return_value=mock_response)
            response = await http_client.get("https://api.example.com/data")

        assert response == mock_response
        http_client.rate_limiter.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_params_and_headers(self, http_client):
        """Test GET request with params and headers."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        async with http_client:
            request_mock = AsyncMock(return_value=mock_response)
            http_client._client.request = request_mock
            await http_client.get(
                "https://api.example.com/data",
                params={"page": 1},
                headers={"Accept": "application/json"},
            )

        request_mock.assert_called_once()
        call_args = request_mock.call_args
        assert call_args[0] == ("GET", "https://api.example.com/data")
        assert call_args[1]["params"] == {"page": 1}
        assert call_args[1]["headers"] == {"Accept": "application/json"}

    @pytest.mark.asyncio
    async def test_post_with_json(self, http_client):
        """Test POST request with JSON body."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.raise_for_status = MagicMock()

        async with http_client:
            request_mock = AsyncMock(return_value=mock_response)
            http_client._client.request = request_mock
            response = await http_client.post(
                "https://api.example.com/data",
                json={"name": "test"},
            )

        assert response == mock_response
        request_mock.assert_called_with(
            "POST", "https://api.example.com/data", json={"name": "test"}, data=None, headers=None
        )

    @pytest.mark.asyncio
    async def test_head_request(self, http_client):
        """Test HEAD request."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        async with http_client:
            request_mock = AsyncMock(return_value=mock_response)
            http_client._client.request = request_mock
            response = await http_client.head("https://api.example.com/health")

        assert response == mock_response
        request_mock.assert_called_with(
            "HEAD", "https://api.example.com/health", headers=None
        )


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
        mock_tracer,
        mock_metrics,
        mock_logger,
    ):
        """Create client with all observability components."""
        tracer, _ = mock_tracer
        return UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            timeout=10.0,
            provider="test_provider",
            tracer=tracer,
            metrics=mock_metrics,
            logger=mock_logger,
        )

    @pytest.mark.asyncio
    async def test_successful_request_creates_span(
        self, http_client_with_observability, mock_tracer
    ):
        """Test successful request creates tracing span with correct attributes."""
        tracer, span = mock_tracer

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        async with http_client_with_observability:
            http_client_with_observability._client.request = AsyncMock(return_value=mock_response)
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
        self, http_client_with_observability, mock_metrics
    ):
        """Test successful request records duration histogram."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        async with http_client_with_observability:
            http_client_with_observability._client.request = AsyncMock(return_value=mock_response)
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
    async def test_error_records_error_counter(
        self, http_client_with_observability, mock_metrics
    ):
        """Test error increments error counter."""
        async with http_client_with_observability:
            http_client_with_observability._client.request = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            with pytest.raises(httpx.ConnectError):
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

    def test_default_observability_uses_noop(
        self, mock_rate_limiter
    ):
        """Test client uses NoOp implementations when observability not provided."""
        from bioetl.domain.ports import NoOpMetrics, NoOpTracing

        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
        )

        assert isinstance(client._tracer, NoOpTracing)
        assert isinstance(client._metrics, NoOpMetrics)

    def test_provider_attribute_set(self, mock_rate_limiter):
        """Test provider attribute is set correctly."""
        client = UnifiedHTTPClient(
            rate_limiter=mock_rate_limiter,
            provider="chembl",
        )
        assert client.provider == "chembl"
