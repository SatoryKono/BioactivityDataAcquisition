"""Юнит-тесты для HttpClientMiddleware: retry, rate-limit, circuit breaker."""
from __future__ import annotations
import logging
from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.errors import ClientNetworkError, ClientRateLimitError, ClientResponseError
from bioetl.infrastructure.clients.middleware import HttpClientMiddleware


class _FakeTime:
    """Простая подмена perf_counter/sleep для детерминизма."""

    def __init__(self) -> None:
        self.value = 0.0

    def perf_counter(self) -> float:
        self.value += 0.01
        return self.value

    def sleep(self, delay: float) -> None:
        self.value += delay


@pytest.fixture(autouse=True)
def deterministic_random():
    with patch("random.uniform", return_value=0.0):
        yield


@pytest.fixture
def base_client():
    client = MagicMock()
    client.request = MagicMock()
    return client


def _response(status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


def test_retry_on_timeout_then_success(monkeypatch, base_client):
    """Таймауты ретраятся до успеха, задержки не блокируют тест."""
    fake_time = _FakeTime()
    monkeypatch.setattr("time.perf_counter", fake_time.perf_counter)
    monkeypatch.setattr("time.sleep", fake_time.sleep)

    base_client.request.side_effect = [TimeoutError("t1"), TimeoutError("t2"), _response(200)]

    middleware = HttpClientMiddleware(
        provider="chembl",
        base_client=base_client,
        max_attempts=3,
        base_delay=0.1,
        backoff_factor=2.0,
    )

    result = middleware.request("GET", "http://example.com")

    assert result.status_code == 200
    assert base_client.request.call_count == 3


def test_retry_on_rate_limit_then_success(monkeypatch, base_client):
    """HTTP 429 ведет к ретраю и последующему успеху."""
    fake_time = _FakeTime()
    monkeypatch.setattr("time.perf_counter", fake_time.perf_counter)
    monkeypatch.setattr("time.sleep", fake_time.sleep)

    base_client.request.side_effect = [_response(429), _response(200)]

    middleware = HttpClientMiddleware(
        provider="chembl",
        base_client=base_client,
        max_attempts=2,
        base_delay=0.05,
    )

    result = middleware.request("GET", "http://example.com/rate")

    assert result.status_code == 200
    assert base_client.request.call_count == 2


def test_retry_logging_and_metrics(monkeypatch, base_client, caplog):
    """Лог ретраев содержит задержку, причину и суммарное ожидание."""
    fake_time = _FakeTime()
    monkeypatch.setattr("time.perf_counter", fake_time.perf_counter)
    monkeypatch.setattr("time.sleep", fake_time.sleep)

    base_client.request.side_effect = [TimeoutError("t1"), _response(200)]

    retry_metric = MagicMock()
    failure_metric = MagicMock()
    middleware = HttpClientMiddleware(
        provider="chembl",
        base_client=base_client,
        max_attempts=2,
        base_delay=0.1,
        backoff_factor=2.0,
        retry_metric_callback=retry_metric,
        failure_metric_callback=failure_metric,
    )

    caplog.set_level(logging.INFO)
    result = middleware.request("GET", "http://example.com")

    assert result.status_code == 200
    retry_record = next(rec for rec in caplog.records if rec.message == "Retrying HTTP request")
    success_record = next(rec for rec in caplog.records if rec.message == "HTTP request succeeded")

    assert retry_record.delay == pytest.approx(0.1)
    assert retry_record.total_retry_delay == pytest.approx(0.1)
    assert retry_record.retry_reason == "TimeoutError"
    assert success_record.total_retry_delay == pytest.approx(0.1)
    assert success_record.attempts == 2
    retry_metric.assert_called_once_with(1)
    failure_metric.assert_not_called()


def test_server_error_retries_until_give_up(monkeypatch, base_client):
    """500 ошибки ретраятся и приводят к ClientResponseError после лимита."""
    fake_time = _FakeTime()
    monkeypatch.setattr("time.perf_counter", fake_time.perf_counter)
    monkeypatch.setattr("time.sleep", fake_time.sleep)

    failing = _response(500)
    base_client.request.return_value = failing

    middleware = HttpClientMiddleware(
        provider="chembl",
        base_client=base_client,
        max_attempts=2,
        base_delay=0.01,
    )

    with pytest.raises(ClientResponseError):
        middleware.request("GET", "http://example.com/500")

    assert base_client.request.call_count == 2


def test_final_failure_logging_and_metrics(monkeypatch, base_client, caplog):
    """Итоговый лог при неуспехе содержит количество попыток и общее ожидание."""
    fake_time = _FakeTime()
    monkeypatch.setattr("time.perf_counter", fake_time.perf_counter)
    monkeypatch.setattr("time.sleep", fake_time.sleep)

    failing = _response(500)
    base_client.request.return_value = failing

    retry_metric = MagicMock()
    failure_metric = MagicMock()
    middleware = HttpClientMiddleware(
        provider="chembl",
        base_client=base_client,
        max_attempts=2,
        base_delay=0.01,
        retry_metric_callback=retry_metric,
        failure_metric_callback=failure_metric,
    )

    caplog.set_level(logging.INFO)
    with pytest.raises(ClientResponseError):
        middleware.request("GET", "http://example.com/500")

    final_failure = next(
        rec for rec in caplog.records if rec.message == "HTTP request failed after retries"
    )

    assert final_failure.attempts == 2
    assert final_failure.total_retry_delay == pytest.approx(0.01)
    retry_metric.assert_called_once_with(1)
    failure_metric.assert_called_once_with(1)


def test_circuit_breaker_blocks_and_recovers(monkeypatch, base_client):
    """Circuit breaker открывается, блокирует и закрывается после таймаута."""
    fake_time = _FakeTime()
    monkeypatch.setattr("time.perf_counter", fake_time.perf_counter)
    monkeypatch.setattr("time.sleep", fake_time.sleep)

    success = _response(200)
    base_client.request.side_effect = [
        TimeoutError("t1"),
        TimeoutError("t2"),  # Открывает выключатель
        success,
    ]

    middleware = HttpClientMiddleware(
        provider="chembl",
        base_client=base_client,
        max_attempts=2,
        base_delay=0.01,
        circuit_breaker_threshold=2,
        circuit_breaker_recovery_time=0.5,
    )

    with pytest.raises(ClientNetworkError):
        middleware.request("GET", "http://example.com/unreliable")

    open_at = middleware._circuit_opened_at  # noqa: SLF001
    assert open_at is not None

    with pytest.raises(ClientNetworkError):
        middleware.request("GET", "http://example.com/unreliable")
    assert base_client.request.call_count == 2

    fake_time.value = open_at + middleware.circuit_breaker_recovery_time + 0.1

    recovered = middleware.request("GET", "http://example.com/unreliable")

    assert recovered.status_code == 200
    assert base_client.request.call_count == 3
    assert middleware._circuit_opened_at is None  # noqa: SLF001

