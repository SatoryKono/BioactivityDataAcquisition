"""Socket-free lifecycle regressions for the HTTP health server."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

import bioetl.interfaces.http.health_server as health_server_module
from bioetl.interfaces.http.health_server import (
    HealthServer,
    HealthServerControlPlaneDeps,
)


pytestmark = pytest.mark.unit


def test_constructor_preserves_legacy_dependencies_and_rejects_ambiguous_kwargs() -> (
    None
):
    """Legacy callers remain supported, while ambiguous/unknown wiring fails closed."""
    monitor = MagicMock()
    exposition = MagicMock()
    exposition.build_exposition.return_value = "metric 1\n"

    server = HealthServer(
        health_monitor=monitor,
        metrics_exposition=exposition,
        runtime_source_id="runtime-a",
        prometheus_base_url="http://prometheus:9090/",
    )

    assert server._health_monitor is monitor
    assert server._runtime_source_id == "runtime-a"
    assert server._handle_metrics() == "metric 1\n"
    assert server._prometheus_base_url == "http://prometheus:9090"

    with pytest.raises(TypeError, match="unexpected keyword argument.*unknown_port"):
        HealthServer(unknown_port=object())

    with pytest.raises(TypeError, match="either control_plane or legacy port kwargs"):
        HealthServer(
            control_plane=HealthServerControlPlaneDeps(),
            health_monitor=monitor,
        )


def test_default_metrics_and_mutable_runtime_context_are_available_without_socket() -> (
    None
):
    """Default exposition and late-bound context do not require a listening socket."""
    clock = MagicMock()
    server = HealthServer()

    server.set_data_root("/data")
    server.set_clock(clock)

    assert "bioetl_health_server_scrape_up 1" in server._handle_metrics()
    assert server._data_root == "/data"
    assert server._clock is clock
    assert server.uptime_seconds == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_start_and_stop_delegate_to_asyncio_server_without_real_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lifecycle owns listener, refresh task, and structured start/stop events."""
    listener = MagicMock()
    listener.is_serving.return_value = True
    listener.wait_closed = AsyncMock()
    start_server = AsyncMock(return_value=listener)
    refresh = AsyncMock()
    periodic_refresh = AsyncMock()
    logger = MagicMock()
    refresher = MagicMock()
    monkeypatch.setattr(health_server_module.asyncio, "start_server", start_server)
    monkeypatch.setattr(health_server_module, "refresh_control_plane_metrics", refresh)
    monkeypatch.setattr(
        health_server_module,
        "run_periodic_control_plane_metrics_refresh",
        periodic_refresh,
    )

    server = HealthServer(
        host="127.0.0.2",
        port=8123,
        control_plane=HealthServerControlPlaneDeps(
            control_plane_integrity_refresher=refresher,
        ),
        logger=logger,
    )
    await server.start()
    await asyncio.sleep(0)

    assert server.is_running is True
    assert server.uptime_seconds >= 0
    start_server.assert_awaited_once_with(
        server._handle_connection,
        "127.0.0.2",
        8123,
        reuse_address=False,
    )
    refresh.assert_awaited_once_with(refresher)
    periodic_refresh.assert_awaited_once_with(
        refresher,
        interval_seconds=server._control_plane_integrity_refresh_interval_seconds,
    )
    logger.info.assert_any_call(
        "health_server_started",
        host="127.0.0.2",
        port=8123,
    )

    await server.stop()

    listener.close.assert_called_once_with()
    listener.wait_closed.assert_awaited_once_with()
    assert server.is_running is False
    assert server._control_plane_integrity_refresh_task is None
    logger.info.assert_called_with("health_server_stopped")


@pytest.mark.asyncio
@pytest.mark.parametrize("with_logger", [False, True])
async def test_bind_failure_is_reported_and_propagated(
    monkeypatch: pytest.MonkeyPatch,
    *,
    with_logger: bool,
) -> None:
    """A bind error is never swallowed; logging remains optional."""
    logger = MagicMock() if with_logger else None
    bind_error = OSError("address unavailable")
    monkeypatch.setattr(
        health_server_module.asyncio,
        "start_server",
        AsyncMock(side_effect=bind_error),
    )
    server = HealthServer(host="127.0.0.1", port=8124, logger=logger)

    with pytest.raises(OSError, match="address unavailable"):
        await server.start()

    if logger is not None:
        logger.warning.assert_called_once_with(
            "health_server_bind_failed",
            host="127.0.0.1",
            port=8124,
            error="address unavailable",
            reason_code="HEALTH_SERVER_BIND_FAILED",
        )


@pytest.mark.asyncio
async def test_run_health_server_forwards_dependencies_and_stops_on_cancellation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The convenience runner always releases its server on cancellation."""
    started = asyncio.Event()
    instances: list[object] = []

    class _FakeHealthServer:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs
            self.clock: object | None = None
            self.stopped = False
            instances.append(self)

        def set_clock(self, clock: object | None) -> None:
            self.clock = clock

        async def start(self) -> None:
            started.set()

        async def stop(self) -> None:
            self.stopped = True

    monkeypatch.setattr(health_server_module, "HealthServer", _FakeHealthServer)
    monitor = MagicMock()
    clock = MagicMock()
    task = asyncio.create_task(
        health_server_module.run_health_server(
            host="127.0.0.3",
            port=8125,
            health_monitor=monitor,
            clock=clock,
        )
    )
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    instance = instances[0]
    assert instance.kwargs["host"] == "127.0.0.3"
    assert instance.kwargs["port"] == 8125
    assert instance.kwargs["control_plane"].health_monitor is monitor
    assert instance.clock is clock
    assert instance.stopped is True
