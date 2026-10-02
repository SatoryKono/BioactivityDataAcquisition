"""Anonymous pacing covers health probes, requests and rate-limit retries."""

from types import SimpleNamespace

import httpx
import pytest

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
async def test_health_data_and_retry_share_anonymous_budget(monkeypatch):
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

    settings = SimpleNamespace(test_mode=False)
    config = HttpClientFactory._resolve_config("semanticscholar", settings)
    assert config.rate == 0.01
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
    assert requests[1][1] - requests[0][1] >= 100
    assert requests[2][1] - requests[1][1] >= 120
