"""Unit tests for detached observability backend runtime helpers."""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    ObservabilityBackendEnsureResult,
    _build_detached_backend_popen_kwargs,
    _build_detached_backend_env,
    _build_observability_backend_probe_urls,
    build_observability_backend_health_url,
    ensure_observability_backend_started,
    probe_observability_backend,
    start_detached_quarantine_backend,
    should_disable_transient_health_server,
    wait_for_observability_backend_ready,
)


def test_build_observability_backend_health_url_uses_host_and_port() -> None:
    assert (
        build_observability_backend_health_url(host="127.0.0.1", port=8081)
        == "http://127.0.0.1:8081/health"
    )


def test_build_observability_backend_probe_urls_prefers_liveness_first() -> None:
    assert _build_observability_backend_probe_urls("http://127.0.0.1:8081/health") == (
        "http://127.0.0.1:8081/health/live",
        "http://127.0.0.1:8081/health",
    )


def test_probe_observability_backend_uses_liveness_then_fallback() -> None:
    calls: list[str] = []

    class _Response:
        status = 200

        def __enter__(self) -> _Response:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

    def fake_urlopen(url: str, timeout: float) -> _Response:
        calls.append(url)
        if url.endswith("/health/live"):
            raise OSError("liveness not ready")
        return _Response()

    assert (
        probe_observability_backend(
            "http://127.0.0.1:8081/health",
            timeout_seconds=1.0,
            urlopen_fn=fake_urlopen,
        )
        is True
    )
    assert calls == [
        "http://127.0.0.1:8081/health/live",
        "http://127.0.0.1:8081/health",
    ]


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


def test_build_detached_backend_env_prefixes_src_pythonpath() -> None:
    env = _build_detached_backend_env(current_env={"PYTHONPATH": "existing-path"})

    assert "PYTHONPATH" in env
    pythonpath = env["PYTHONPATH"].split(os.pathsep)
    assert pythonpath[0].endswith("/src") or pythonpath[0].endswith("\\src")
    assert pythonpath[1] == "existing-path"


def test_start_detached_quarantine_backend_sets_repo_cwd_and_env() -> None:
    captured: dict[str, object] = {}

    class _Process:
        args = ["python", "-m", "bioetl"]

    def fake_popen(command: list[str], **kwargs: object) -> _Process:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return _Process()

    start_detached_quarantine_backend(
        bind_host="0.0.0.0",
        port=8081,
        python_executable="python",
        popen_factory=fake_popen,
    )

    kwargs = captured["kwargs"]
    assert captured["command"] == [
        "python",
        "-m",
        "bioetl",
        "quarantine",
        "serve",
        "--host",
        "0.0.0.0",
        "--port",
        "8081",
    ]
    assert isinstance(kwargs, dict)
    assert str(kwargs["cwd"]).endswith("BioactivityDataAcquisition2")
    assert "env" in kwargs
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert "PYTHONPATH" in env


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
