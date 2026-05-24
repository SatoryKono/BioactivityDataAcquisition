"""Runtime helpers for self-managed observability backend startup.

The Grafana Quarantine Explorer datasource requires a long-lived HTTP backend
that survives one-shot pipeline commands. These helpers probe the backend and
start ``bioetl quarantine serve`` in detached mode when needed.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
)
from bioetl.interfaces.cli.formatters import echo_info, echo_warning

if TYPE_CHECKING:
    from collections.abc import Callable

DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST = "127.0.0.1"
DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST = "0.0.0.0"
DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS = 8.0
DEFAULT_OBSERVABILITY_BACKEND_POLL_SECONDS = 0.25

_DETACHED_STATUS = frozenset({"reused", "started"})


@dataclass(frozen=True, slots=True)
class ObservabilityBackendEnsureResult:
    """Structured result for one backend ensure attempt."""

    status: str
    health_url: str
    pid: int | None = None
    command: tuple[str, ...] = ()
    message: str | None = None

    @property
    def backend_available(self) -> bool:
        """Return whether a long-lived backend is ready after the ensure step."""
        return self.status in _DETACHED_STATUS


def build_observability_backend_health_url(
    *,
    host: str = DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST,
    port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> str:
    """Build the canonical backend health URL used for readiness probes."""
    return f"http://{host}:{port}/health"


def probe_observability_backend(
    health_url: str,
    *,
    timeout_seconds: float = 1.0,
    urlopen_fn: Callable[..., object] = urlopen,
) -> bool:
    """Return True when the observability backend responds successfully."""
    try:
        with urlopen_fn(health_url, timeout=timeout_seconds) as response:
            status = getattr(response, "status", 200)
            return int(status) < 400
    except (HTTPError, URLError, OSError, ValueError):
        return False


def _build_detached_backend_popen_kwargs(
    *,
    os_name: str = os.name,
    subprocess_module: object = subprocess,
) -> dict[str, object]:
    """Build platform-specific detached subprocess kwargs for the backend."""
    kwargs: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os_name == "nt":
        detached_process = int(getattr(subprocess_module, "DETACHED_PROCESS", 0))
        new_process_group = int(
            getattr(subprocess_module, "CREATE_NEW_PROCESS_GROUP", 0)
        )
        create_no_window = int(getattr(subprocess_module, "CREATE_NO_WINDOW", 0))
        kwargs["creationflags"] = (
            detached_process | new_process_group | create_no_window
        )

        startupinfo_factory = getattr(subprocess_module, "STARTUPINFO", None)
        if callable(startupinfo_factory):
            startupinfo = startupinfo_factory()
            startf_use_show_window = int(
                getattr(subprocess_module, "STARTF_USESHOWWINDOW", 0)
            )
            has_sw_hide = hasattr(subprocess_module, "SW_HIDE")
            sw_hide = int(getattr(subprocess_module, "SW_HIDE", 0))
            if startf_use_show_window:
                startupinfo.dwFlags = (
                    int(getattr(startupinfo, "dwFlags", 0)) | startf_use_show_window
                )
            if has_sw_hide:
                startupinfo.wShowWindow = sw_hide
            kwargs["startupinfo"] = startupinfo
    else:
        kwargs["start_new_session"] = True
    return kwargs


def start_detached_quarantine_backend(
    *,
    bind_host: str = DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST,
    port: int = DEFAULT_HEALTH_SERVER_PORT,
    python_executable: str | None = None,
    popen_factory: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> subprocess.Popen[bytes]:
    """Launch ``bioetl quarantine serve`` as a detached background process."""
    command = [
        python_executable or sys.executable,
        "-m",
        "bioetl",
        "quarantine",
        "serve",
        "--host",
        bind_host,
        "--port",
        str(port),
    ]
    kwargs = _build_detached_backend_popen_kwargs()
    return popen_factory(command, **kwargs)


def wait_for_observability_backend_ready(
    health_url: str,
    *,
    timeout_seconds: float = DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS,
    poll_seconds: float = DEFAULT_OBSERVABILITY_BACKEND_POLL_SECONDS,
    probe_fn: Callable[..., bool] = probe_observability_backend,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> bool:
    """Poll the backend health URL until it responds or timeout expires."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if probe_fn(health_url):
            return True
        sleep_fn(poll_seconds)
    return probe_fn(health_url)


def ensure_observability_backend_started(
    *,
    enabled: bool,
    port: int = DEFAULT_HEALTH_SERVER_PORT,
    probe_host: str = DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST,
    bind_host: str = DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST,
    ready_timeout_seconds: float = DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS,
    poll_seconds: float = DEFAULT_OBSERVABILITY_BACKEND_POLL_SECONDS,
    probe_fn: Callable[..., bool] = probe_observability_backend,
    start_fn: Callable[
        ..., subprocess.Popen[bytes]
    ] = start_detached_quarantine_backend,
    wait_fn: Callable[..., bool] = wait_for_observability_backend_ready,
    info_printer: Callable[[str], None] = echo_info,
    warning_printer: Callable[[str], None] = echo_warning,
) -> ObservabilityBackendEnsureResult:
    """Ensure the detached observability backend is running for Grafana panels."""
    health_url = build_observability_backend_health_url(host=probe_host, port=port)
    if not enabled:
        return ObservabilityBackendEnsureResult(
            status="disabled",
            health_url=health_url,
            message="Observability backend auto-start disabled by CLI flag.",
        )

    if probe_fn(health_url):
        info_printer(f"Observability backend: reusing {health_url}")
        return ObservabilityBackendEnsureResult(
            status="reused",
            health_url=health_url,
            message=f"Observability backend already ready at {health_url}.",
        )

    try:
        process = start_fn(bind_host=bind_host, port=port)
    except OSError as exc:
        warning_printer(
            "Observability backend: failed to start detached Quarantine Explorer "
            f"backend on port {port} ({exc}). Grafana ID panels may remain empty."
        )
        return ObservabilityBackendEnsureResult(
            status="failed",
            health_url=health_url,
            message=str(exc),
        )

    ready = wait_fn(
        health_url,
        timeout_seconds=ready_timeout_seconds,
        poll_seconds=poll_seconds,
        probe_fn=probe_fn,
    )
    command = (
        python_executable_to_tuple(process.args) if hasattr(process, "args") else ()
    )
    if ready:
        info_printer(f"Observability backend: started {health_url}")
        return ObservabilityBackendEnsureResult(
            status="started",
            health_url=health_url,
            pid=getattr(process, "pid", None),
            command=command,
            message=f"Started detached Quarantine Explorer backend at {health_url}.",
        )

    warning_printer(
        "Observability backend: detached Quarantine Explorer process did not "
        f"become ready at {health_url}. Grafana ID panels may remain empty."
    )
    return ObservabilityBackendEnsureResult(
        status="failed",
        health_url=health_url,
        pid=getattr(process, "pid", None),
        command=command,
        message=f"Detached backend did not become ready at {health_url}.",
    )


def should_disable_transient_health_server(
    *,
    health_server_enabled: bool,
    health_port: int,
    observability_backend_port: int,
    backend_result: ObservabilityBackendEnsureResult,
) -> bool:
    """Return True when the detached backend should replace the in-process server."""
    return (
        health_server_enabled
        and backend_result.backend_available
        and health_port == observability_backend_port
    )


def python_executable_to_tuple(args: object) -> tuple[str, ...]:
    """Normalize subprocess ``args`` into a tuple for stable reporting/tests."""
    if isinstance(args, (list, tuple)):
        return tuple(str(item) for item in args)
    return (str(args),)


__all__ = [
    "DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST",
    "DEFAULT_OBSERVABILITY_BACKEND_POLL_SECONDS",
    "DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST",
    "DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS",
    "ObservabilityBackendEnsureResult",
    "build_observability_backend_health_url",
    "ensure_observability_backend_started",
    "probe_observability_backend",
    "python_executable_to_tuple",
    "should_disable_transient_health_server",
    "start_detached_quarantine_backend",
    "wait_for_observability_backend_ready",
]
