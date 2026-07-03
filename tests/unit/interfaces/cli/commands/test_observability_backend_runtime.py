"""Unit tests for detached observability backend runtime helpers."""

from __future__ import annotations

import os
import signal
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.error import HTTPError

import bioetl.interfaces.cli.commands.domains.health.observability_backend_failure_details as failure_details_subject
import bioetl.interfaces.cli.commands.domains.health.observability_backend_process as process_subject
import bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime as runtime_subject
import pytest
from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    ObservabilityBackendEnsureResult,
    _build_detached_backend_popen_kwargs,
    _build_detached_backend_env,
    _build_observability_backend_probe_urls,
    build_observability_backend_required_probe_paths,
    build_detached_backend_log_path,
    build_observability_backend_health_url,
    probe_observability_backend_required_paths,
    ensure_observability_backend_started,
    probe_observability_backend,
    start_detached_quarantine_backend,
    should_disable_transient_health_server,
    wait_for_observability_backend_required_paths_ready,
    wait_for_observability_backend_ready,
)


pytestmark = pytest.mark.unit


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


def test_build_observability_backend_required_probe_paths_adds_catalog_and_pipelines() -> (
    None
):
    assert build_observability_backend_required_probe_paths(
        pipelines=("chembl_target", "chembl_activity", "chembl_target"),
    ) == (
        "/ops/control-plane/filter-options?dimension=pipeline&response_shape=list",
        "/ops/control-plane/checkpoint-freshness?pipeline=chembl_activity",
        "/ops/control-plane/checkpoint-freshness?pipeline=chembl_target",
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


def test_probe_observability_backend_required_paths_uses_backend_base_url() -> None:
    calls: list[str] = []

    class _Response:
        status = 200

        def __enter__(self) -> _Response:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

    def fake_urlopen(url: str, timeout: float) -> _Response:
        calls.append(url)
        return _Response()

    assert (
        probe_observability_backend_required_paths(
            "http://127.0.0.1:8081/health",
            required_probe_paths=(
                "/ops/control-plane/checkpoint-freshness?pipeline=x",
            ),
            timeout_seconds=1.0,
            urlopen_fn=fake_urlopen,
        )
        is True
    )
    assert calls == [
        "http://127.0.0.1:8081/ops/control-plane/checkpoint-freshness?pipeline=x"
    ]


def test_describe_required_probe_failure_includes_http_status_and_body() -> None:
    def fake_urlopen(_url: str, timeout: float) -> object:
        raise HTTPError(
            url="http://127.0.0.1:8081/ops/control-plane/checkpoint-freshness?pipeline=x",
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=BytesIO(b"Control-plane selector catalog unavailable"),
        )

    detail = runtime_subject._describe_required_probe_failure(
        "http://127.0.0.1:8081/health",
        required_probe_paths=("/ops/control-plane/checkpoint-freshness?pipeline=x",),
        urlopen_fn=fake_urlopen,
    )

    assert detail is not None
    assert "HTTP 503 Service Unavailable" in detail
    assert "Control-plane selector catalog unavailable" in detail


def test_open_url_uses_standard_library_opener(monkeypatch: pytest.MonkeyPatch) -> None:
    opener = MagicMock()
    build_opener = MagicMock(return_value=opener)
    monkeypatch.setattr(failure_details_subject, "build_opener", build_opener)

    failure_details_subject._open_url("http://127.0.0.1:8081/health", timeout=1.5)

    build_opener.assert_called_once_with()
    opener.open.assert_called_once_with(
        "http://127.0.0.1:8081/health",
        timeout=1.5,
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
    wait_required = MagicMock(return_value=True)
    info = MagicMock()

    result = ensure_observability_backend_started(
        enabled=True,
        port=8082,
        probe_fn=probe,
        start_fn=start,
        wait_fn=wait,
        wait_required_paths_fn=wait_required,
        info_printer=info,
    )

    assert result.status == "started"
    assert result.backend_available is True
    assert result.pid == 321
    assert result.command == ("python", "-m", "bioetl")
    start.assert_called_once_with(bind_host="0.0.0.0", port=8082)
    wait.assert_called_once()
    wait_required.assert_called_once()
    info.assert_called_once()


def test_ensure_backend_restarts_bound_but_unresponsive_listener() -> None:
    probe = MagicMock(return_value=False)
    listener_pid = MagicMock(return_value=4321)
    drop = MagicMock(return_value=True)
    process = MagicMock(pid=777, args=["python", "-m", "bioetl"])
    start = MagicMock(return_value=process)
    wait = MagicMock(return_value=True)
    wait_required = MagicMock(return_value=True)
    warning = MagicMock()

    result = ensure_observability_backend_started(
        enabled=True,
        probe_fn=probe,
        listener_pid_fn=listener_pid,
        drop_stale_backend_fn=drop,
        start_fn=start,
        wait_fn=wait,
        wait_required_paths_fn=wait_required,
        warning_printer=warning,
    )

    assert result.status == "started"
    listener_pid.assert_called_once_with(8081)
    drop.assert_called_once_with(8081)
    start.assert_called_once()
    assert "health probes timeout" in warning.call_args.args[0]


def test_ensure_backend_fails_when_unresponsive_listener_cannot_be_dropped() -> None:
    result = ensure_observability_backend_started(
        enabled=True,
        probe_fn=MagicMock(return_value=False),
        listener_pid_fn=MagicMock(return_value=4321),
        drop_stale_backend_fn=MagicMock(return_value=False),
        start_fn=MagicMock(),
    )

    assert result.status == "failed"
    assert "pid=4321" in (result.message or "")
    assert "health probes timeout" in (result.message or "")


def test_ensure_backend_restarts_stale_backend_missing_required_paths() -> None:
    probe = MagicMock(return_value=True)
    required_probe = MagicMock(return_value=False)
    drop = MagicMock(return_value=True)
    process = MagicMock(pid=777, args=["python", "-m", "bioetl"])
    start = MagicMock(return_value=process)
    wait = MagicMock(return_value=True)
    wait_required = MagicMock(return_value=True)
    warning = MagicMock()
    info = MagicMock()

    result = ensure_observability_backend_started(
        enabled=True,
        probe_fn=probe,
        required_probe_paths=("/ops/control-plane/checkpoint-freshness?pipeline=x",),
        required_probe_fn=required_probe,
        drop_stale_backend_fn=drop,
        start_fn=start,
        wait_fn=wait,
        wait_required_paths_fn=wait_required,
        warning_printer=warning,
        info_printer=info,
    )

    assert result.status == "started"
    required_probe.assert_called_once()
    drop.assert_called_once_with(8081)
    start.assert_called_once()
    wait.assert_called_once()
    wait_required.assert_called_once()
    warning.assert_called_once()


def test_ensure_backend_fails_when_stale_backend_cannot_be_dropped() -> None:
    result = ensure_observability_backend_started(
        enabled=True,
        probe_fn=MagicMock(return_value=True),
        required_probe_paths=("/ops/control-plane/checkpoint-freshness?pipeline=x",),
        required_probe_fn=MagicMock(return_value=False),
        drop_stale_backend_fn=MagicMock(return_value=False),
        start_fn=MagicMock(),
    )

    assert result.status == "failed"
    assert "missing required audit capabilities" in (result.message or "")


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
    assert "startup log:" in (result.message or "").lower()


def test_ensure_backend_failure_message_includes_exit_code_and_log_tail() -> None:
    port = 18081
    log_path = build_detached_backend_log_path(port)
    log_path.write_text("Traceback line\nRuntimeError: boom\n", encoding="utf-8")
    try:
        probe = MagicMock(return_value=False)
        process = MagicMock(pid=654, args=["python", "-m", "bioetl"])
        process.poll.return_value = 7
        start = MagicMock(return_value=process)
        wait = MagicMock(return_value=False)

        result = ensure_observability_backend_started(
            enabled=True,
            port=port,
            probe_fn=probe,
            start_fn=start,
            wait_fn=wait,
        )

        assert result.status == "failed"
        assert "exit code: 7" in (result.message or "").lower()
        assert "RuntimeError: boom" in (result.message or "")
    finally:
        log_path.unlink(missing_ok=True)


def test_wait_for_observability_backend_required_paths_ready_retries_until_success() -> (
    None
):
    checks = {"count": 0}

    def fake_required_probe(
        _health_url: str,
        *,
        required_probe_paths: tuple[str, ...],
        timeout_seconds: float,
    ) -> bool:
        checks["count"] += 1
        assert timeout_seconds == 5.0
        return checks["count"] >= 3 and bool(required_probe_paths)

    sleeps: list[float] = []

    result = wait_for_observability_backend_required_paths_ready(
        "http://127.0.0.1:8081/health",
        required_probe_paths=("/ops/control-plane/checkpoint-freshness?pipeline=x",),
        timeout_seconds=0.05,
        poll_seconds=0.0,
        required_probe_fn=fake_required_probe,
        sleep_fn=sleeps.append,
    )

    assert result is True
    assert checks["count"] >= 3


def test_ensure_backend_reuse_uses_required_probe_timeout() -> None:
    probe = MagicMock(return_value=True)
    required_probe = MagicMock(return_value=True)

    result = ensure_observability_backend_started(
        enabled=True,
        probe_fn=probe,
        required_probe_paths=("/ops/control-plane/checkpoint-freshness?pipeline=x",),
        required_probe_fn=required_probe,
        required_probe_timeout_seconds=9.0,
        start_fn=MagicMock(),
    )

    assert result.status == "reused"
    required_probe.assert_called_once_with(
        "http://127.0.0.1:8081/health",
        required_probe_paths=("/ops/control-plane/checkpoint-freshness?pipeline=x",),
        timeout_seconds=9.0,
    )


def test_ensure_backend_fails_when_required_paths_never_become_ready() -> None:
    probe = MagicMock(return_value=False)
    process = MagicMock(pid=654, args=["python", "-m", "bioetl"])
    start = MagicMock(return_value=process)
    wait = MagicMock(return_value=True)
    wait_required = MagicMock(return_value=False)
    warning = MagicMock()

    result = ensure_observability_backend_started(
        enabled=True,
        probe_fn=probe,
        required_probe_paths=("/ops/control-plane/checkpoint-freshness?pipeline=x",),
        start_fn=start,
        wait_fn=wait,
        wait_required_paths_fn=wait_required,
        warning_printer=warning,
    )

    assert result.status == "failed"
    assert "required audit capabilities" in (result.message or "")
    wait.assert_called_once()
    wait_required.assert_called_once()
    warning.assert_called_once()


def test_ensure_backend_failed_startup_appends_process_diagnostics_to_log(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "backend.log"
    monkeypatch.setattr(runtime_subject, "build_detached_backend_log_path", lambda _port: log_path)
    monkeypatch.setattr(
        runtime_subject,
        "_describe_required_probe_failure",
        MagicMock(return_value="Capability probe failed: timeout."),
    )
    probe = MagicMock(return_value=False)
    process = MagicMock(pid=654, args=["python", "-m", "bioetl", "quarantine", "serve"])
    process.poll.return_value = None

    result = ensure_observability_backend_started(
        enabled=True,
        probe_fn=probe,
        start_fn=MagicMock(return_value=process),
        wait_fn=MagicMock(return_value=True),
        wait_required_paths_fn=MagicMock(return_value=False),
        required_probe_paths=("/ops/control-plane/checkpoint-freshness?pipeline=x",),
    )

    assert result.status == "failed"
    log_text = log_path.read_text(encoding="utf-8")
    assert "BioETL detached backend diagnostics" in log_text
    assert "child_pid=654" in log_text
    assert "command=python -m bioetl quarantine serve" in log_text
    assert "Capability probe failed: timeout." in log_text


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


def test_drop_listening_backend_on_port_terminates_all_windows_listeners(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {"pids": (111, 222)}
    taskkill_commands: list[list[str]] = []

    def fake_find(_port: int) -> tuple[int, ...]:
        return state["pids"]

    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        taskkill_commands.append(command)
        if command[2] == "111":
            state["pids"] = (222,)
        else:
            state["pids"] = ()
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(process_subject.os, "name", "nt")
    monkeypatch.setattr(process_subject, "_resolve_system_executable", lambda _name: _name)
    monkeypatch.setattr(
        process_subject,
        "_find_listening_backend_pids_by_port",
        fake_find,
    )
    monkeypatch.setattr(process_subject.subprocess, "run", fake_run)

    assert process_subject.drop_listening_backend_on_port(
        8081,
        sleep_fn=lambda _seconds: None,
    )
    assert taskkill_commands == [
        ["taskkill", "/PID", "111", "/T", "/F"],
        ["taskkill", "/PID", "222", "/T", "/F"],
    ]


def test_drop_listening_backend_on_port_falls_back_when_taskkill_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {"pids": (111,)}
    taskkill_commands: list[list[str]] = []
    kill_calls: list[tuple[int, int]] = []

    def fake_find(_port: int) -> tuple[int, ...]:
        return state["pids"]

    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        taskkill_commands.append(command)
        return SimpleNamespace(returncode=1)

    def fake_kill(pid: int, sig: int) -> None:
        kill_calls.append((pid, sig))
        state["pids"] = ()

    monkeypatch.setattr(process_subject.os, "name", "nt")
    monkeypatch.setattr(process_subject, "_resolve_system_executable", lambda _name: _name)
    monkeypatch.setattr(
        process_subject,
        "_find_listening_backend_pids_by_port",
        fake_find,
    )
    monkeypatch.setattr(process_subject.subprocess, "run", fake_run)
    monkeypatch.setattr(process_subject.os, "kill", fake_kill)

    assert process_subject.drop_listening_backend_on_port(
        8081,
        sleep_fn=lambda _seconds: None,
    )
    assert taskkill_commands == [["taskkill", "/PID", "111", "/T", "/F"]]
    assert kill_calls == [(111, signal.SIGTERM)]


def test_find_listening_backend_pids_by_port_returns_empty_when_command_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(process_subject.os, "name", "posix")
    monkeypatch.setattr(process_subject, "_resolve_system_executable", lambda _name: None)

    assert process_subject._find_listening_backend_pids_by_port(8081) == ()


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
    assert "stdout" in kwargs
    assert "stderr" in kwargs
    env = kwargs["env"]
    assert isinstance(env, dict)
    assert "PYTHONPATH" in env


def test_build_detached_backend_log_path_uses_tempdir_and_port() -> None:
    path = build_detached_backend_log_path(8081)

    assert path.name == "bioetl-quarantine-backend-8081.log"
    assert path.parent.exists()


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
