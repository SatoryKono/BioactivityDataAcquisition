"""Real HTTP orchestration distinguishes local waits from provider failures."""

import asyncio
from contextlib import nullcontext
from itertools import pairwise
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest

from bioetl.domain.exceptions import RetryExhaustedError, CircuitBreakerOpenError
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.chembl._health_probe import probe_chembl_status
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.http import request_timing, rate_limiter


def make_client(limiter=None, **kwargs):
    return UnifiedHTTPClient(
        rate_limiter=limiter or TokenBucketRateLimiter(100, 1),
        circuit_breaker=CircuitBreakerGuard(
            provider="chembl", failure_threshold=2, recovery_timeout=10
        ),
        provider="chembl",
        logger=MagicMock(),
        retry_config=RetryConfig(max_attempts=2, base_delay=0.001, max_delay=300),
        **kwargs,
    )


@pytest.mark.asyncio
async def test_health_transport_deadline_excludes_admission_wait():
    class WaitingLimiter:
        async def acquire(self):
            await asyncio.sleep(0.03)

    client = make_client(WaitingLimiter())
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"status": "UP"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        client._client = transport
        result = await probe_chembl_status(
            http_client=client,
            adapter_metrics=SimpleNamespace(measure_request=lambda _: nullcontext()),
            logger=client.logger,
            provider_name="chembl",
            timeout_seconds=0.01,
            health_errors=(TimeoutError, httpx.HTTPError),
            transient_errors=(TimeoutError,),
            handle_response=lambda response: (
                HealthStatus.HEALTHY
                if response.json()["status"] == "UP"
                else HealthStatus.DEGRADED
            ),
        )
    assert result == HealthStatus.HEALTHY
    assert len(requests) == 1
    facts = client.logger.info.call_args.kwargs
    assert facts["admission_seconds"] >= 0.025
    assert facts["transport_seconds"] < 0.01


@pytest.mark.asyncio
async def test_transport_timeout_remains_a_real_failure():
    client = make_client()

    async def respond(request):
        await asyncio.sleep(1)
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        client._client = transport
        with pytest.raises(TimeoutError):
            await client.get_once(
                "https://example.test/health?api_key=secret", request_timeout=0.01
            )
    facts = client.logger.info.call_args.kwargs
    assert facts["phase"] == "transport"
    assert facts["error_type"] == "TimeoutError"
    assert "secret" not in str(client.logger.mock_calls)


@pytest.mark.asyncio
async def test_cancellation_during_admission_never_calls_transport():
    entered = asyncio.Event()

    class WaitingLimiter:
        async def acquire(self):
            entered.set()
            await asyncio.Event().wait()

    client = make_client(WaitingLimiter())
    requests = []
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: requests.append(request))
    ) as transport:
        client._client = transport
        task = asyncio.create_task(client.get_once("https://example.test/health"))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert requests == []
    assert client.circuit_breaker.get_state().value == "CLOSED"
    assert client.logger.info.call_args.kwargs["phase"] == "admission"


def virtual_clock(monkeypatch):
    now = [0.0]

    async def sleep(delay):
        now[0] += delay

    clock = SimpleNamespace(monotonic=lambda: now[0])
    monkeypatch.setattr(request_timing, "time", clock)
    monkeypatch.setattr(rate_limiter, "time", clock)
    monkeypatch.setattr(asyncio, "sleep", sleep)
    return now


@pytest.mark.asyncio
@pytest.mark.parametrize("retry_after", ["0", "250", "invalid"])
async def test_anonymous_semanticscholar_batch_retries_keep_100_second_floor(
    monkeypatch, retry_after
):
    now = virtual_clock(monkeypatch)
    sent = []

    def respond(request):
        sent.append(now[0])
        return (
            httpx.Response(429, headers={"Retry-After": retry_after})
            if len(sent) < 5
            else httpx.Response(200, json=[])
        )

    client = UnifiedHTTPClient(
        rate_limiter=TokenBucketRateLimiter(0.01, 1),
        circuit_breaker=CircuitBreakerGuard(
            provider="semanticscholar", failure_threshold=10, recovery_timeout=600
        ),
        provider="semanticscholar",
        logger=MagicMock(),
        retry_config=RetryConfig(max_attempts=5, base_delay=30, max_delay=300),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        client._client = transport
        response = await client.post(
            "https://example.test/paper/batch", json={"ids": ["DOI:10.1234/test"]}
        )
    assert response.status_code == 200
    assert len(sent) == 5
    floor = 250 if retry_after == "250" else 100
    assert all(right - left >= floor for left, right in pairwise(sent))


@pytest.mark.asyncio
async def test_health_retry_after_delays_following_data_request(monkeypatch):
    now = virtual_clock(monkeypatch)
    sent = []

    def respond(request):
        sent.append(now[0])
        return (
            httpx.Response(429, headers={"Retry-After": "120"})
            if len(sent) == 1
            else httpx.Response(200)
        )

    client = make_client(TokenBucketRateLimiter(0.02, 1))
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        client._client = transport
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_once("https://example.test/health")
        assert (await client.get("https://example.test/data")).status_code == 200
    assert sent == [0.0, 120.0]


@pytest.mark.asyncio
async def test_excessive_retry_after_stops_without_early_retry(monkeypatch):
    now = virtual_clock(monkeypatch)
    sent = []

    def respond(request):
        sent.append(now[0])
        return httpx.Response(429, headers={"Retry-After": "3600"})

    client = make_client()
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        client._client = transport
        with pytest.raises(RetryExhaustedError) as caught:
            await client.get("https://example.test/data")
    assert sent == [0.0]
    assert "wait budget" in str(caught.value.last_error)


@pytest.mark.asyncio
async def test_forbidden_is_not_retried(monkeypatch):
    now = virtual_clock(monkeypatch)
    sent = []

    def respond(request):
        sent.append(now[0])
        return httpx.Response(403)

    client = make_client()
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        client._client = transport
        with pytest.raises(httpx.HTTPStatusError):
            await client.get("https://example.test/data")
    assert sent == [0.0]


@pytest.mark.asyncio
async def test_concurrent_health_and_data_share_one_bucket():
    sent = []

    def respond(request):
        sent.append(asyncio.get_running_loop().time())
        return httpx.Response(200)

    client = make_client(TokenBucketRateLimiter(50, 1))
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        client._client = transport
        await asyncio.gather(
            client.get_once("https://example.test/health"),
            client.get("https://example.test/a"),
            client.get("https://example.test/b"),
        )
    assert len(sent) == 3
    assert all(b - a >= 0.018 for a, b in pairwise(sent))


@pytest.mark.asyncio
async def test_circuit_opens_then_recovers_without_reset(monkeypatch):
    from bioetl.infrastructure.adapters.http import circuit_breaker

    now = virtual_clock(monkeypatch)
    monkeypatch.setattr(circuit_breaker, "_now", lambda: now[0])
    sent = []

    def respond(request):
        sent.append(now[0])
        return httpx.Response(503 if len(sent) <= 2 else 200)

    client = make_client()
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        client._client = transport
        for _ in range(2):
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_once("https://example.test/health")
        with pytest.raises(CircuitBreakerOpenError):
            await client.get_once("https://example.test/health")
        assert len(sent) == 2
        now[0] += 11
        assert (await client.get_once("https://example.test/health")).status_code == 200
    assert client.circuit_breaker.get_state().value == "CLOSED"


@pytest.mark.asyncio
async def test_cancellation_during_transport_is_not_a_retry():
    entered = asyncio.Event()

    async def respond(request):
        entered.set()
        await asyncio.Event().wait()

    client = make_client()
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        client._client = transport
        task = asyncio.create_task(client.get("https://example.test/data"))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert client.logger.info.call_count == 1
    assert client.logger.info.call_args.kwargs["error_type"] == "CancelledError"
