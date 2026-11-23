"""Provider pacing covers health probes, requests and rate-limit retries."""

from itertools import pairwise
from types import SimpleNamespace

import httpx
import pytest

from bioetl.composition.providers._config_helpers import _get_batch_size_from_config
from bioetl.domain.exceptions import RetryExhaustedError
from bioetl.infrastructure.config import load_source_config

from bioetl.composition.factories.datasource.http_client import HttpClientFactory
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter


pytestmark = pytest.mark.unit


def test_invalid_rate_configuration_does_not_fall_back_to_faster_requests(monkeypatch):
    from pydantic import ValidationError

    from bioetl.composition.factories.datasource import http_client
    from bioetl.infrastructure.schemas.base_schemas import BaseRateLimitConfig

    def invalid_config(_provider):
        return BaseRateLimitConfig(requests_per_second=0)

    monkeypatch.setattr(http_client, "load_source_config", invalid_config)
    with pytest.raises(ValidationError):
        HttpClientFactory._resolve_config("semanticscholar", SimpleNamespace())


@pytest.mark.asyncio
@pytest.mark.parametrize("api_key,interval", [(None, 100), ("test-key", 1)])
async def test_health_data_and_retry_share_provider_budget(
    monkeypatch, api_key, interval
):
    from bioetl.infrastructure.adapters.http import rate_limiter as limiter_module

    now = [0.0]
    requests = []

    async def sleep(delay):
        now[0] += delay

    monkeypatch.setattr(
        limiter_module, "time", SimpleNamespace(monotonic=lambda: now[0])
    )
    monkeypatch.setattr(limiter_module.asyncio, "sleep", sleep)
    from bioetl.infrastructure.adapters.http import request_timing

    monkeypatch.setattr(
        request_timing, "time", SimpleNamespace(monotonic=lambda: now[0])
    )

    def respond(request):
        requests.append((request.method, now[0]))
        if len(requests) == 2:
            return httpx.Response(429, headers={"Retry-After": "120"})
        return httpx.Response(200, json={"data": []})

    settings = SimpleNamespace(test_mode=False, semanticscholar_api_key=api_key)
    config = HttpClientFactory._resolve_config("semanticscholar", settings)
    assert config.rate == 1 / interval
    assert config.capacity == 1
    client = UnifiedHTTPClient(
        rate_limiter=TokenBucketRateLimiter(config.rate, config.capacity),
        circuit_breaker=CircuitBreakerGuard(provider="semanticscholar"),
        retry_config=HttpClientFactory._build_retry_config(config, settings),
        provider="semanticscholar",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        client._client = transport
        await client.get_once("https://example.test/health")
        await client.get("https://example.test/data")
    assert len(requests) == 3
    assert requests[1][1] - requests[0][1] >= interval
    assert requests[2][1] - requests[1][1] >= 120


def test_semanticscholar_uses_documented_bulk_lookup_capacity():
    config = load_source_config("semanticscholar")

    assert config.pagination.id_batch_size == 500
    assert config.batch_size == 500
    assert _get_batch_size_from_config("semanticscholar") == 500


@pytest.mark.asyncio
@pytest.mark.parametrize("limited_attempts", [4, 5])
@pytest.mark.parametrize("retry_after", [None, "120"])
async def test_anonymous_rate_limits_recover_or_exhaust_finite_budget(
    monkeypatch, limited_attempts, retry_after
):
    from bioetl.infrastructure.adapters.http import rate_limiter, request_timing

    now = [0.0]
    request_times = []

    async def sleep(delay):
        now[0] += delay

    clock = SimpleNamespace(monotonic=lambda: now[0])
    monkeypatch.setattr(rate_limiter, "time", clock)
    monkeypatch.setattr(rate_limiter.asyncio, "sleep", sleep)
    monkeypatch.setattr(request_timing, "time", clock)

    def respond(request):
        request_times.append(now[0])
        if len(request_times) <= limited_attempts:
            headers = {"Retry-After": retry_after} if retry_after is not None else {}
            return httpx.Response(429, headers=headers)
        return httpx.Response(200, json=[{"paperId": "synthetic-paper"}])

    settings = SimpleNamespace(test_mode=False, semanticscholar_api_key=None)
    config = HttpClientFactory._resolve_config("semanticscholar", settings)
    retry = HttpClientFactory._build_retry_config(config, settings)
    assert retry.max_attempts == 5
    client = UnifiedHTTPClient(
        rate_limiter=TokenBucketRateLimiter(config.rate, config.capacity),
        circuit_breaker=CircuitBreakerGuard(provider="semanticscholar"),
        retry_config=retry,
        provider="semanticscholar",
    )
    url = "https://example.test/paper/batch"
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        client._client = transport
        if limited_attempts < retry.max_attempts:
            response = await client.post(url, json={"ids": ["synthetic-paper"]})
            assert response.json() == [{"paperId": "synthetic-paper"}]
        else:
            with pytest.raises(RetryExhaustedError):
                await client.post(url, json={"ids": ["synthetic-paper"]})
    assert len(request_times) == 5
    for attempt, (previous, current) in enumerate(pairwise(request_times)):
        expected_delay = (
            float(retry_after)
            if retry_after is not None
            else retry.calculate_delay(attempt, url)
        )
        assert current - previous >= max(100, expected_delay)
