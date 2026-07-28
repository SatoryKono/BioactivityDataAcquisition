"""ARCH-CR-03: health-server resource cleanup contracts."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from bioetl.interfaces.cli.commands.domains.health import server_integration_deps as deps
from bioetl.interfaces.cli.commands.domains.health import (
    server_integration_lifecycle as lifecycle,
)
from bioetl.interfaces.cli.commands.domains.health import (
    server_integration_observability as observability,
)


@pytest.mark.asyncio
async def test_close_health_server_resources_closes_quarantine_after_checkpoint_error() -> (
    None
):
    checkpoint = AsyncMock()
    checkpoint.aclose = AsyncMock(side_effect=RuntimeError("checkpoint boom"))
    quarantine = AsyncMock()
    quarantine.aclose = AsyncMock()
    deps_obj = SimpleNamespace(checkpoint_port=checkpoint)

    with pytest.raises(RuntimeError, match="checkpoint boom"):
        await deps.close_health_server_resources(
            deps=deps_obj,  # type: ignore[arg-type]
            quarantine_service=quarantine,  # type: ignore[arg-type]
        )

    checkpoint.aclose.assert_awaited_once()
    quarantine.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_server_context_cleans_up_on_non_oserror_start_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    close_mock = AsyncMock()
    server = SimpleNamespace(
        start=AsyncMock(side_effect=RuntimeError("bind logic failed")),
        stop=AsyncMock(),
    )
    monkeypatch.setattr(
        lifecycle._deps,
        "get_health_server_dependencies",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        lifecycle._deps,
        "_get_optional_health_server_quarantine_service",
        lambda: None,
    )
    monkeypatch.setattr(lifecycle._deps, "build_health_server", lambda **_: server)
    monkeypatch.setattr(lifecycle._deps, "close_health_server_resources", close_mock)

    with pytest.raises(RuntimeError, match="bind logic failed"):
        async with lifecycle.health_server_context(enabled=True):
            pass

    close_mock.assert_awaited_once()
    server.stop.assert_not_awaited()


def test_start_health_observability_logs_ready_only_when_started(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, dict[str, Any]]] = []

    class _Logger:
        def info(self, event: str, **kwargs: Any) -> None:
            events.append((event, kwargs))

        def warning(self, event: str, **kwargs: Any) -> None:
            events.append((event, kwargs))

    settings = SimpleNamespace(
        observability=SimpleNamespace(
            metrics_enabled=True,
            metrics_server_enabled=True,
            metrics_fail_fast=False,
            metrics_retry_count=0,
            metrics_retry_delay=0.0,
        ),
        metrics_port=9100,
        metrics_addr="127.0.0.1",
    )
    monkeypatch.setattr(observability, "get_runtime_settings", lambda: settings)
    monkeypatch.setattr(
        observability,
        "get_metrics_server_starter",
        lambda: (lambda **_: False),
    )

    observability._start_health_observability(logger=_Logger())  # type: ignore[arg-type]

    assert events
    assert events[0][0] == "health_server_metrics_not_started"
    assert events[0][1]["metrics_started"] is False
