"""Composite health probes share admission without hiding failure or cancellation."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.chembl import ChemblAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.health import (
    HealthProbeCoordinator,
    provider_execution_scope,
    resolve_provider_resources,
)

pytestmark = pytest.mark.unit


def test_provider_resources_are_shared_only_inside_one_execution():
    with provider_execution_scope():
        first = resolve_provider_resources("chembl", 0.1, 1)
        assert resolve_provider_resources("chembl", 0.1, 1) is first
        assert resolve_provider_resources("other", 0.1, 1) is not first
        with provider_execution_scope():
            assert resolve_provider_resources("chembl", 0.1, 1) is not first
        assert resolve_provider_resources("chembl", 0.1, 1) is first
    assert resolve_provider_resources("chembl", 0.1, 1) is not first


@pytest.mark.asyncio
@pytest.mark.parametrize("recover", [False, True])
async def test_parallel_enrichers_share_two_attempts_and_keep_each_result(recover):
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []

    async def request(*args, **kwargs):
        calls.append(kwargs)
        entered.set()
        await release.wait()
        if not recover or len(calls) == 1:
            raise httpx.ReadTimeout("provider timed out")
        return httpx.Response(200, json={"status": "UP"})

    coordinator = HealthProbeCoordinator()
    clients = [MagicMock(), MagicMock()]
    adapters = []
    for client in clients:
        client.get_once = AsyncMock(side_effect=request)
        client.health_probe_coordinator = coordinator
        adapters.append(ChemblAdapter(http_client=client, logger=MagicMock()))
    tasks = [asyncio.create_task(adapter.check_health()) for adapter in adapters]
    await entered.wait()
    await asyncio.sleep(0)
    release.set()
    results = await asyncio.gather(*tasks)
    expected = HealthStatus.HEALTHY if recover else HealthStatus.DEGRADED
    assert [result.status for result in results] == [expected, expected]
    assert all(adapter._last_probe_health_status == expected for adapter in adapters)
    assert len(calls) == 2
    assert all(call["request_timeout"] == 5.0 for call in calls)
    await adapters[0].check_health()
    assert len(calls) > 2  # Completed health results must never become a cache.


@pytest.mark.asyncio
async def test_cancelled_waiter_does_not_cancel_other_child():
    coordinator = HealthProbeCoordinator()
    entered, release = asyncio.Event(), asyncio.Event()

    async def probe():
        entered.set()
        await release.wait()
        return HealthStatus.DEGRADED

    first = asyncio.create_task(coordinator.run("status", probe))
    second = asyncio.create_task(coordinator.run("status", probe))
    await entered.wait()
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    release.set()
    assert await second == HealthStatus.DEGRADED
    assert coordinator._pending == {}


@pytest.mark.asyncio
async def test_adapter_two_transport_timeouts_preserve_admission_timing(monkeypatch):
    class WaitingLimiter:
        async def acquire(self):
            await asyncio.sleep(0.02)

    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.chembl.health.CHEMBL_HEALTH_PROBE_TIMEOUT_SECONDS",
        0.005,
    )
    logger = MagicMock()
    client = UnifiedHTTPClient(
        rate_limiter=WaitingLimiter(),
        circuit_breaker=CircuitBreakerGuard(
            provider="chembl", failure_threshold=3, recovery_timeout=10
        ),
        logger=logger,
    )
    calls = []

    async def respond(request):
        calls.append(request)
        await asyncio.Event().wait()

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        client._client = transport
        adapter = ChemblAdapter(http_client=client, logger=logger)
        result = await adapter.check_health()
    assert result.status == HealthStatus.DEGRADED
    assert len(calls) == 2
    attempts = [
        call.kwargs
        for call in logger.info.call_args_list
        if call.args == ("http_attempt_completed",)
    ]
    assert len(attempts) == 2
    assert all(attempt["admission_seconds"] >= 0.015 for attempt in attempts)
    assert all(attempt["transport_seconds"] >= 0.005 for attempt in attempts)
    assert all(attempt["error_type"] == "TimeoutError" for attempt in attempts)


@pytest.mark.asyncio
async def test_last_cancelled_waiter_drains_the_probe():
    coordinator = HealthProbeCoordinator()
    entered, stopped = asyncio.Event(), asyncio.Event()

    async def probe():
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    task = asyncio.create_task(coordinator.run("status", probe))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert stopped.is_set()
    assert coordinator._pending == {}
