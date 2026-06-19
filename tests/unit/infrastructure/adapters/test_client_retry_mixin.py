"""Unit tests for HTTPClientRetryMixin.

Tests retry delay calculation, Retry-After header handling, retry budget
enforcement, jitter, metrics recording, and logging behaviour.

Source: src/bioetl/infrastructure/adapters/http/client_retry_mixin.py
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from bioetl.domain.ports.noop import NoOpTracing
from bioetl.domain.exceptions import (
    CircuitBreakerOpenError,
    RecoverableError,
    RetryExhaustedError,
)
from bioetl.domain.resilience import RetryConfig
from bioetl.infrastructure.adapters.http.client_retry_mixin import HTTPClientRetryMixin


pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers — minimal concrete subclass that satisfies mixin dependencies
# ---------------------------------------------------------------------------


class _ConcreteRetryClient(HTTPClientRetryMixin):
    """Minimal concrete class providing all attributes the mixin reads."""

    def __init__(
        self,
        retry_config: RetryConfig,
        provider: str = "test_provider",
        logger: MagicMock | None = None,
        tracer: MagicMock | None = None,
    ) -> None:
        self.retry_config = retry_config
        self.provider = provider
        self.logger = logger
        self.run_id = "test-run-001"
        self._metrics = MagicMock()
        self.rate_limiter = AsyncMock()
        self.circuit_breaker = AsyncMock()
        self._tracer = tracer if tracer is not None else NoOpTracing()
        self._client = AsyncMock(spec=httpx.AsyncClient)

    def _get_client(self) -> AsyncMock:
        return self._client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def default_config() -> RetryConfig:
    """RetryConfig with zero jitter for deterministic delay checks."""
    return RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        multiplier=2.0,
        jitter_range=(0.0, 0.0),
        max_delay=60.0,
    )


@pytest.fixture
def mock_logger() -> MagicMock:
    logger = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def client(default_config: RetryConfig, mock_logger: MagicMock) -> _ConcreteRetryClient:
    return _ConcreteRetryClient(
        retry_config=default_config,
        provider="chembl",
        logger=mock_logger,
    )


@pytest.fixture
def mock_span() -> MagicMock:
    span = MagicMock()
    span.__enter__ = MagicMock(return_value=span)
    span.__exit__ = MagicMock(return_value=None)
    span.set_attribute = MagicMock()
    span.record_exception = MagicMock()
    return span


@pytest.fixture
def mock_tracing(mock_span: MagicMock) -> tuple[MagicMock, MagicMock, MagicMock]:
    otel_tracer = MagicMock()
    otel_tracer.start_as_current_span = MagicMock(return_value=mock_span)

    tracing = MagicMock()
    tracing.get_tracer = MagicMock(return_value=otel_tracer)

    return tracing, otel_tracer, mock_span


async def _passthrough_circuit_breaker_call(func, *args, **kwargs):
    """Execute wrapped request function without changing its semantics."""
    return await func(*args, **kwargs)


# ---------------------------------------------------------------------------
# _handle_retry_delay — sleep duration and Retry-After override
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_retry_delay_sleeps_for_calculated_duration(
    client: _ConcreteRetryClient,
) -> None:
    """_handle_retry_delay should sleep for the delay returned by retry_config."""
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        returned = await client._handle_retry_delay(
            attempt=0, url="https://api.example.com"
        )

    # With zero jitter: base_delay * multiplier^0 = 1.0
    assert returned == pytest.approx(1.0)
    mock_sleep.assert_awaited_once_with(pytest.approx(1.0))


@pytest.mark.asyncio
async def test_handle_retry_delay_exponential_backoff(
    client: _ConcreteRetryClient,
) -> None:
    """Delay doubles with each attempt when multiplier=2 and jitter=0."""
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        delay_0 = await client._handle_retry_delay(attempt=0)
        delay_1 = await client._handle_retry_delay(attempt=1)
        delay_2 = await client._handle_retry_delay(attempt=2)

    assert delay_0 == pytest.approx(1.0)
    assert delay_1 == pytest.approx(2.0)
    assert delay_2 == pytest.approx(4.0)
    assert mock_sleep.await_count == 3


@pytest.mark.asyncio
async def test_handle_retry_delay_honors_retry_after_header(
    client: _ConcreteRetryClient,
) -> None:
    """Retry-After header value replaces calculated delay (within max_delay)."""
    response = MagicMock(spec=httpx.Response)
    response.headers = {"Retry-After": "10.0"}

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        returned = await client._handle_retry_delay(
            attempt=0, url="", response=response
        )

    # clamp_retry_after(10.0) with max_delay=60 → 10.0
    assert returned == pytest.approx(10.0)
    mock_sleep.assert_awaited_once_with(pytest.approx(10.0))


@pytest.mark.asyncio
async def test_handle_retry_delay_ignores_invalid_retry_after(
    client: _ConcreteRetryClient,
) -> None:
    """Non-numeric Retry-After header falls back to calculated delay."""
    response = MagicMock(spec=httpx.Response)
    response.headers = {"Retry-After": "not-a-number"}

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        returned = await client._handle_retry_delay(attempt=0, response=response)

    # Falls back to calculated delay = 1.0 (attempt 0, no jitter)
    assert returned == pytest.approx(1.0)
    mock_sleep.assert_awaited_once_with(pytest.approx(1.0))


@pytest.mark.asyncio
async def test_handle_retry_delay_clamps_retry_after_to_max_delay(
    default_config: RetryConfig,
) -> None:
    """Retry-After value exceeding max_delay is clamped to max_delay."""
    config = RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        multiplier=2.0,
        jitter_range=(0.0, 0.0),
        max_delay=30.0,
    )
    client = _ConcreteRetryClient(retry_config=config)
    response = MagicMock(spec=httpx.Response)
    response.headers = {"Retry-After": "9999"}

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        returned = await client._handle_retry_delay(attempt=0, response=response)

    assert returned == pytest.approx(30.0)
    mock_sleep.assert_awaited_once_with(pytest.approx(30.0))


# ---------------------------------------------------------------------------
# _can_retry — budget and last-attempt logic
# ---------------------------------------------------------------------------


def test_can_retry_returns_true_within_budget(client: _ConcreteRetryClient) -> None:
    """Should return True when attempt is not the last and retries remain."""
    # max_attempts=3 → budget=2; attempt=0, retries_used=0 → can retry
    assert client._can_retry(attempt=0, retries_used=0) is True


def test_can_retry_returns_false_on_last_attempt(client: _ConcreteRetryClient) -> None:
    """Should return False when attempt index is the final allowed."""
    # is_last_attempt(2) is True for max_attempts=3
    assert client._can_retry(attempt=2, retries_used=0) is False


def test_can_retry_returns_false_when_budget_exhausted(
    client: _ConcreteRetryClient,
) -> None:
    """Should return False when retry budget is fully consumed."""
    # budget=2, retries_used=2 → exhausted
    assert client._can_retry(attempt=0, retries_used=2) is False


def test_can_retry_with_explicit_budget_per_request() -> None:
    """retry_budget_per_request caps effective retries below max_attempts-1."""
    config = RetryConfig(
        max_attempts=5, retry_budget_per_request=1, jitter_range=(0.0, 0.0)
    )
    client = _ConcreteRetryClient(retry_config=config)

    # Budget of 1: first retry allowed, second is not
    assert client._can_retry(attempt=0, retries_used=0) is True
    assert client._can_retry(attempt=0, retries_used=1) is False


# ---------------------------------------------------------------------------
# _record_retry_budget_exhausted — metrics and log output
# ---------------------------------------------------------------------------


def test_record_retry_budget_exhausted_increments_counter(
    client: _ConcreteRetryClient,
) -> None:
    """Should call _metrics.increment_counter with the correct metric name."""
    client._record_retry_budget_exhausted(method="GET", url="https://api.example.com")

    client._metrics.increment_counter.assert_called_once_with(
        "bioetl_http_retry_budget_exhausted_total",
        1,
        {"provider": "chembl", "method": "GET"},
    )


def test_record_retry_budget_exhausted_logs_warning(
    client: _ConcreteRetryClient, mock_logger: MagicMock
) -> None:
    """Should emit a structured warning log with provider and method info."""
    client._record_retry_budget_exhausted(
        method="post", url="https://api.example.com/data"
    )

    mock_logger.warning.assert_called_once()
    call_kwargs = mock_logger.warning.call_args
    # First positional arg is the log event name
    assert call_kwargs[0][0] == "http_retry_budget_exhausted"
    assert call_kwargs[1]["run_id"] == "test-run-001"


def test_record_retry_budget_exhausted_silent_without_logger(
    default_config: RetryConfig,
) -> None:
    """Should not raise when no logger is configured."""
    client = _ConcreteRetryClient(retry_config=default_config, logger=None)
    client._record_retry_budget_exhausted(method="GET", url="https://example.com")
    # If no exception is raised, the test passes


# ---------------------------------------------------------------------------
# _record_request_metrics — histogram and counter calls
# ---------------------------------------------------------------------------


def test_record_request_metrics_observes_histogram(
    client: _ConcreteRetryClient,
) -> None:
    """Should observe request duration in the histogram."""
    client._record_request_metrics(
        method="GET", duration=0.5, status_code=200, retries=0, last_error=None
    )

    client._metrics.observe_histogram.assert_called_once_with(
        "bioetl_http_request_duration_seconds",
        0.5,
        {"provider": "chembl", "method": "GET", "status": "200"},
    )


def test_record_request_metrics_records_retries(client: _ConcreteRetryClient) -> None:
    """Should increment retry counter when retries > 0."""
    client._record_request_metrics(
        method="GET", duration=1.0, status_code=200, retries=2, last_error=None
    )

    client._metrics.increment_counter.assert_called_with(
        "bioetl_http_retries_total",
        2,
        {"provider": "chembl", "method": "GET"},
    )


def test_record_request_metrics_records_error_on_4xx(
    client: _ConcreteRetryClient,
) -> None:
    """Should increment error counter for 4xx status codes."""
    client._record_request_metrics(
        method="GET", duration=0.3, status_code=404, retries=0, last_error=None
    )

    calls = [call[0][0] for call in client._metrics.increment_counter.call_args_list]
    assert "bioetl_http_request_errors_total" in calls


def test_record_request_metrics_uses_exception_type_for_error_label(
    client: _ConcreteRetryClient,
) -> None:
    """Error counter label should reflect the exception type name."""
    err = ConnectionError("timed out")
    client._record_request_metrics(
        method="GET", duration=0.1, status_code=0, retries=1, last_error=err
    )

    error_call = None
    for call in client._metrics.increment_counter.call_args_list:
        if call[0][0] == "bioetl_http_request_errors_total":
            error_call = call
            break

    assert error_call is not None
    labels = error_call[0][2]
    assert labels["error_type"] == "ConnectionError"


def test_record_request_metrics_skips_retry_counter_when_no_retries(
    client: _ConcreteRetryClient,
) -> None:
    """Should not emit the retries counter when retries == 0 and status is 200."""
    client._record_request_metrics(
        method="GET", duration=0.2, status_code=200, retries=0, last_error=None
    )

    called_metrics = [c[0][0] for c in client._metrics.increment_counter.call_args_list]
    assert "bioetl_http_retries_total" not in called_metrics


# ---------------------------------------------------------------------------
# _log_retry — structured log emission
# ---------------------------------------------------------------------------


def test_log_retry_emits_structured_warning(
    client: _ConcreteRetryClient, mock_logger: MagicMock
) -> None:
    """_log_retry should emit a warning with attempt, wait, and provider info."""
    client._log_retry(
        url="https://api.example.com",
        method="GET",
        attempt=0,
        wait_seconds=1.5,
        status_code=503,
    )

    mock_logger.warning.assert_called_once()
    args, kwargs = mock_logger.warning.call_args
    assert args[0] == "Retrying request"
    assert kwargs.get("provider") == "chembl"
    assert kwargs.get("run_id") == "test-run-001"
    assert kwargs.get("attempt") == 1  # 0-indexed → displayed as 1


def test_log_retry_silent_without_logger(default_config: RetryConfig) -> None:
    """_log_retry should be a no-op when logger is None."""
    client = _ConcreteRetryClient(retry_config=default_config, logger=None)
    # Should not raise
    client._log_retry(
        url="https://example.com", method="GET", attempt=0, wait_seconds=1.0
    )


def test_log_retry_uses_reason_when_no_status_code(
    client: _ConcreteRetryClient, mock_logger: MagicMock
) -> None:
    """When reason is provided and no status_code, reason string is logged."""
    client._log_retry(
        url="https://api.example.com",
        method="POST",
        attempt=1,
        wait_seconds=2.0,
        reason="connection refused",
    )

    mock_logger.warning.assert_called_once()
    _, kwargs = mock_logger.warning.call_args
    assert "connection refused" in str(kwargs.get("reason", ""))


# ---------------------------------------------------------------------------
# _is_retryable_error — classification of exception types
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exc",
    [
        httpx.ConnectError("conn refused"),
        httpx.ConnectTimeout("timed out"),
        httpx.ReadTimeout("read timeout"),
        httpx.ReadError("read error"),
        httpx.WriteError("write error"),
    ],
)
def test_is_retryable_error_returns_true_for_httpx_transport_errors(
    client: _ConcreteRetryClient,
    exc: Exception,
) -> None:
    """Common httpx transport errors must be classified as retryable."""
    assert client._is_retryable_error(exc) is True


def test_is_retryable_error_returns_true_for_recoverable_error(
    client: _ConcreteRetryClient,
) -> None:
    """RecoverableError subclass must be classified as retryable."""

    class _SomeRecoverable(RecoverableError):
        pass

    assert client._is_retryable_error(_SomeRecoverable("transient")) is True


def test_is_retryable_error_returns_false_for_value_error(
    client: _ConcreteRetryClient,
) -> None:
    """ValueError is not retryable by default."""
    assert client._is_retryable_error(ValueError("bad input")) is False


def test_is_retryable_error_returns_true_for_retryable_http_status(
    client: _ConcreteRetryClient,
) -> None:
    """HTTPStatusError with a retryable status code must be classified as retryable."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 503
    exc = httpx.HTTPStatusError(
        "Service Unavailable", request=MagicMock(), response=mock_response
    )
    assert client._is_retryable_error(exc) is True


def test_is_retryable_error_returns_false_for_non_retryable_http_status(
    client: _ConcreteRetryClient,
) -> None:
    """HTTPStatusError with a non-retryable status code must not be retried."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 400
    exc = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=mock_response
    )
    assert client._is_retryable_error(exc) is False


def test_is_retryable_error_custom_retryable_exception_type() -> None:
    """Custom exception types added to retryable_exceptions must be retryable."""
    config = RetryConfig(
        retryable_exceptions=(ConnectionError, TimeoutError, OSError),
        jitter_range=(0.0, 0.0),
    )
    client = _ConcreteRetryClient(retry_config=config)
    assert client._is_retryable_error(OSError("disk error")) is True


# ---------------------------------------------------------------------------
# Characterization — full retry loop and attempt semantics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_with_retry_honors_retry_after_in_full_flow(
    default_config: RetryConfig,
    mock_logger: MagicMock,
    mock_tracing: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    """503 + Retry-After should sleep for the header value before retrying."""
    tracing, _, span = mock_tracing
    client = _ConcreteRetryClient(
        retry_config=default_config,
        provider="chembl",
        logger=mock_logger,
        tracer=tracing,
    )
    request = httpx.Request("GET", "https://api.example.com/data")
    client._client.request.side_effect = [
        httpx.Response(503, headers={"Retry-After": "7.0"}, request=request),
        httpx.Response(200, json={"status": "ok"}, request=request),
    ]
    client.circuit_breaker.call.side_effect = _passthrough_circuit_breaker_call

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        response = await client._request_with_retry(
            "GET",
            "https://api.example.com/data",
        )

    assert response.status_code == 200
    mock_sleep.assert_awaited_once_with(pytest.approx(7.0))
    client._metrics.increment_counter.assert_any_call(
        "bioetl_http_retries_total",
        1,
        {"provider": "chembl", "method": "GET"},
    )
    attributes = (
        tracing.get_tracer.return_value.start_as_current_span.call_args.kwargs[
            "attributes"
        ]
    )
    assert attributes["bioetl.provider"] == "chembl"
    assert attributes["bioetl.run_id"] == "test-run-001"
    span.__enter__.assert_called_once()
    span.__exit__.assert_called_once()
    span_calls = [call.args for call in span.set_attribute.call_args_list]
    assert ("http.status_code", 200) in span_calls
    assert ("http.retries", 1) in span_calls


@pytest.mark.asyncio
async def test_request_with_retry_finalizes_span_and_metrics_on_retry_exhausted(
    default_config: RetryConfig,
    mock_logger: MagicMock,
    mock_tracing: tuple[MagicMock, MagicMock, MagicMock],
) -> None:
    """Retry exhaustion should mark span error, record exception, and flush metrics."""
    tracing, _, span = mock_tracing
    client = _ConcreteRetryClient(
        retry_config=default_config,
        provider="chembl",
        logger=mock_logger,
        tracer=tracing,
    )
    client._client.request.side_effect = httpx.ConnectError("Connection failed")
    client.circuit_breaker.call.side_effect = _passthrough_circuit_breaker_call

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RetryExhaustedError) as exc_info:
            await client._request_with_retry("GET", "https://api.example.com/data")

    assert exc_info.value.attempts == default_config.max_attempts
    assert isinstance(exc_info.value.last_error, httpx.ConnectError)
    span_calls = [call.args for call in span.set_attribute.call_args_list]
    assert ("error", True) in span_calls
    assert ("error.type", "retry_exhausted") in span_calls
    assert ("http.retries", 2) in span_calls
    assert any(name == "bioetl.duration_ms" for name, _ in span_calls)
    span.record_exception.assert_called_once()
    span.__exit__.assert_called_once()

    error_calls = [
        call
        for call in client._metrics.increment_counter.call_args_list
        if call.args[0] == "bioetl_http_request_errors_total"
    ]
    assert len(error_calls) == 1
    assert error_calls[0].args[2]["error_type"] == "ConnectError"


@pytest.mark.asyncio
async def test_request_with_retry_records_retry_budget_exhaustion_end_to_end(
    mock_logger: MagicMock,
) -> None:
    """End-to-end flow should emit retry-budget exhaustion signal once budget blocks retries."""
    config = RetryConfig(
        max_attempts=5,
        retry_budget_per_request=1,
        jitter_range=(0.0, 0.0),
    )
    client = _ConcreteRetryClient(
        retry_config=config,
        provider="chembl",
        logger=mock_logger,
    )
    client._client.request.side_effect = httpx.ConnectError("Connection failed")
    client.circuit_breaker.call.side_effect = _passthrough_circuit_breaker_call

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RetryExhaustedError) as exc_info:
            await client._request_with_retry("GET", "https://api.example.com/data")

    assert exc_info.value.attempts == 2
    client._metrics.increment_counter.assert_any_call(
        "bioetl_http_retry_budget_exhausted_total",
        1,
        {"provider": "chembl", "method": "GET"},
    )
    mock_logger.warning.assert_any_call(
        "http_retry_budget_exhausted",
        provider="chembl",
        run_id="test-run-001",
        method="GET",
        url="https://api.example.com/data",
        retry_budget=1,
        max_attempts=5,
    )


@pytest.mark.asyncio
async def test_attempt_request_non_retryable_error_marks_span_and_reraises(
    client: _ConcreteRetryClient,
    mock_span: MagicMock,
) -> None:
    """Non-retryable exceptions should be surfaced immediately with span error markers."""
    client._execute_single_attempt = AsyncMock(side_effect=ValueError("bad input"))  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="bad input"):
        await client._attempt_request(
            client._get_client(),
            "GET",
            "https://api.example.com/data",
            0,
            0,
            mock_span,
            {},
        )

    span_calls = [call.args for call in mock_span.set_attribute.call_args_list]
    assert ("error", True) in span_calls
    assert ("error.type", "ValueError") in span_calls
    mock_span.record_exception.assert_called_once()


@pytest.mark.asyncio
async def test_attempt_request_circuit_breaker_open_marks_span_and_logs(
    default_config: RetryConfig,
    mock_logger: MagicMock,
    mock_span: MagicMock,
) -> None:
    """Circuit breaker open should never be converted into retry outcome."""
    client = _ConcreteRetryClient(
        retry_config=default_config,
        provider="chembl",
        logger=mock_logger,
    )
    client._execute_single_attempt = AsyncMock(  # type: ignore[method-assign]
        side_effect=CircuitBreakerOpenError("chembl", "Circuit is open")
    )

    with pytest.raises(CircuitBreakerOpenError):
        await client._attempt_request(
            client._get_client(),
            "GET",
            "https://api.example.com/data",
            0,
            0,
            mock_span,
            {},
        )

    span_calls = [call.args for call in mock_span.set_attribute.call_args_list]
    assert ("error", True) in span_calls
    assert ("error.type", "circuit_breaker_open") in span_calls
    mock_span.record_exception.assert_called_once()
    mock_logger.warning.assert_called_once()
    assert mock_logger.warning.call_args.args[0] == "http_circuit_breaker_open"
    assert mock_logger.warning.call_args.kwargs["run_id"] == "test-run-001"
