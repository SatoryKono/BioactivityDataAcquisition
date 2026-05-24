"""Unit tests for detached observability backend runtime helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    ObservabilityBackendEnsureResult,
    _build_detached_backend_popen_kwargs,
    build_observability_backend_health_url,
    ensure_observability_backend_started,
    should_disable_transient_health_server,
    wait_for_observability_backend_ready,
)


def test_build_observability_backend_health_url_uses_host_and_port() -> None:
    assert (
        build_observability_backend_health_url(host="127.0.0.1", port=8081)
        == "http://127.0.0.1:8081/health"
    )


def test_ensure_backend_returns_disabled_when_flag_is_off() -> None:
    probe = MagicMock()
    start = MagicMock()

    result = ensure_observability_backend_started(
        enabled=False,
        probe_fn=probe,
        start_fn=start,
    )

    assert result.status == "disabled"
    probe.assert_not_called()
    start.assert_not_called()


def test_ensure_backend_reuses_existing_process() -> None:
    probe = MagicMock(return_value=True)
    start = MagicMock()
    info = MagicMock()

    result = ensure_observability_backend_started(
        enabled=True,
        port=9090,
        probe_fn=probe,
        start_fn=start,
        info_printer=info,
    )

    assert result.status == "reused"
    assert result.backend_available is True
    assert result.health_url == "http://127.0.0.1:9090/health"
    start.assert_not_called()
    info.assert_called_once()


def test_ensure_backend_starts_detached_process_when_probe_fails() -> None:
    probe = MagicMock(return_value=False)
    process = MagicMock(pid=321, args=["python", "-m", "bioetl"])
    start = MagicMock(return_value=process)
    wait = MagicMock(return_value=True)
    info = MagicMock()

    result = ensure_observability_backend_started(
        enabled=True,
        port=8082,
        probe_fn=probe,
        start_fn=start,
        wait_fn=wait,
        info_printer=info,
    )

    assert result.status == "started"
    assert result.backend_available is True
    assert result.pid == 321
    assert result.command == ("python", "-m", "bioetl")
    start.assert_called_once_with(bind_host="0.0.0.0", port=8082)
    wait.assert_called_once()
    info.assert_called_once()


def test_ensure_backend_warns_when_detached_process_does_not_become_ready() -> None:
    probe = MagicMock(return_value=False)
    process = MagicMock(pid=654, args=["python", "-m", "bioetl"])
    start = MagicMock(return_value=process)
    wait = MagicMock(return_value=False)
    warning = MagicMock()

    result = ensure_observability_backend_started(
        enabled=True,
        probe_fn=probe,
        start_fn=start,
        wait_fn=wait,
        warning_printer=warning,
    )

    assert result.status == "failed"
    assert result.backend_available is False
    warning.assert_called_once()


def test_ensure_backend_warns_when_start_raises_oserror() -> None:
    warning = MagicMock()

    result = ensure_observability_backend_started(
        enabled=True,
        probe_fn=MagicMock(return_value=False),
        start_fn=MagicMock(side_effect=OSError("bind failed")),
        warning_printer=warning,
    )

    assert result.status == "failed"
    assert "bind failed" in (result.message or "")
    warning.assert_called_once()


def test_wait_for_backend_ready_polls_until_success() -> None:
    probe = MagicMock(side_effect=[False, False, True])
    sleep = MagicMock()

    ready = wait_for_observability_backend_ready(
        "http://127.0.0.1:8081/health",
        timeout_seconds=1.0,
        poll_seconds=0.1,
        probe_fn=probe,
        sleep_fn=sleep,
    )

    assert ready is True
    assert probe.call_count == 3
    assert sleep.call_count == 2


def test_build_detached_backend_popen_kwargs_uses_new_session_on_posix() -> None:
    kwargs = _build_detached_backend_popen_kwargs(os_name="posix")

    assert kwargs["start_new_session"] is True
    assert "creationflags" not in kwargs
    assert "startupinfo" not in kwargs


def test_build_detached_backend_popen_kwargs_hides_windows_console() -> None:
    startupinfo = SimpleNamespace(dwFlags=0, wShowWindow=5)
    fake_subprocess = SimpleNamespace(
        DETACHED_PROCESS=0x00000008,
        CREATE_NEW_PROCESS_GROUP=0x00000200,
        CREATE_NO_WINDOW=0x08000000,
        STARTF_USESHOWWINDOW=0x00000001,
        SW_HIDE=0,
        STARTUPINFO=lambda: startupinfo,
    )

    kwargs = _build_detached_backend_popen_kwargs(
        os_name="nt",
        subprocess_module=fake_subprocess,
    )

    assert kwargs["creationflags"] == 0x08000208
    assert kwargs["startupinfo"] is startupinfo
    assert startupinfo.dwFlags == 0x00000001
    assert startupinfo.wShowWindow == 0


def test_should_disable_transient_health_server_only_on_matching_live_backend() -> None:
    live_backend = ObservabilityBackendEnsureResult(
        status="started",
        health_url="http://127.0.0.1:8081/health",
    )
    failed_backend = ObservabilityBackendEnsureResult(
        status="failed",
        health_url="http://127.0.0.1:8081/health",
    )

    assert (
        should_disable_transient_health_server(
            health_server_enabled=True,
            health_port=8081,
            observability_backend_port=8081,
            backend_result=live_backend,
        )
        is True
    )
    assert (
        should_disable_transient_health_server(
            health_server_enabled=True,
            health_port=9090,
            observability_backend_port=8081,
            backend_result=live_backend,
        )
        is False
    )
    assert (
        should_disable_transient_health_server(
            health_server_enabled=True,
            health_port=8081,
            observability_backend_port=8081,
            backend_result=failed_backend,
        )
        is False
    )
