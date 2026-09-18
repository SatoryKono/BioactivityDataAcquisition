"""Stream B APP: leftover health-service observer and probe-context branches."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.ops.health_service import (
    HealthService,
    _NullAsyncContext,
)

pytestmark = pytest.mark.unit


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=UTC)


class _SimpleAdapter:
    async def health_check(self) -> str:
        return "healthy"


class _CtxAdapter:
    async def __aenter__(self) -> _CtxAdapter:
        return self

    async def __aexit__(self, *_a: object) -> None:
        return None

    async def health_check(self) -> str:
        return "healthy"


class _NestedHttp:
    def __init__(self) -> None:
        self.http_client = _CtxAdapter()


@pytest.mark.asyncio
async def test_check_providers_observer_and_simple_probe() -> None:
    seen: list[str] = []
    factory = SimpleNamespace(
        list_providers=lambda: ["pubchem"],
        create=lambda _name: _SimpleAdapter(),
    )
    service = HealthService(
        logger=MagicMock(),
        _factory=factory,  # type: ignore[arg-type]
        clock=_Clock(),
        result_observer=lambda result: seen.append(result.provider),
    )
    summary = await service.check_providers(["pubchem"])
    assert seen == ["pubchem"]
    assert summary.results["pubchem"].status == "healthy"


@pytest.mark.asyncio
async def test_probe_context_adapter_http_nested_and_null() -> None:
    service = HealthService(
        logger=MagicMock(),
        _factory=SimpleNamespace(list_providers=lambda: [], create=lambda _n: object()),  # type: ignore[arg-type]
        clock=_Clock(),
    )
    ctx_adapter = _CtxAdapter()
    assert service._health_probe_context(ctx_adapter) is ctx_adapter
    nested = SimpleNamespace(_client=_NestedHttp(), http_client=None)
    ctx = service._health_probe_context(nested)
    assert ctx is nested._client.http_client
    async with service._health_probe_context(object()):
        pass
    async with _NullAsyncContext():
        pass


@pytest.mark.asyncio
async def test_run_simple_health_check_and_healthcheck_port() -> None:
    service = HealthService(
        logger=MagicMock(),
        _factory=SimpleNamespace(list_providers=lambda: [], create=lambda _n: object()),  # type: ignore[arg-type]
        clock=_Clock(),
    )
    adapter = _SimpleAdapter()
    status = await service._run_simple_health_check(adapter, adapter.health_check)
    assert status == "healthy"
