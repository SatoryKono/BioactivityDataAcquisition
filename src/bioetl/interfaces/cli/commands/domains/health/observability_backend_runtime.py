"""Runtime helpers for self-managed observability backend startup.

The Grafana Quarantine Explorer datasource requires a long-lived HTTP backend
that survives one-shot pipeline commands. These helpers probe the backend and
start ``bioetl quarantine serve`` in detached mode when needed.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from bioetl.interfaces.cli.commands.domains.health.observability_backend_process import (
    _build_detached_backend_env,
    _build_detached_backend_popen_kwargs,
    build_detached_backend_log_path,
    drop_listening_backend_on_port,
    python_executable_to_tuple,
    start_detached_quarantine_backend,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
)
from bioetl.interfaces.cli.formatters import echo_info, echo_warning

if TYPE_CHECKING:
    from collections.abc import Callable

DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST = "127.0.0.1"
DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST = "0.0.0.0"
DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS = 20.0
DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PATHS_READY_TIMEOUT_SECONDS = 60.0
DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PROBE_TIMEOUT_SECONDS = 5.0
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


def _build_observability_backend_probe_urls(health_url: str) -> tuple[str, ...]:
    """Return canonical readiness probe URLs for one backend base health URL."""
    if health_url.endswith("/health"):
        live_url = f"{health_url}/live"
        return (live_url, health_url)
    return (health_url,)


def probe_observability_backend(
    health_url: str,
    *,
    timeout_seconds: float = 1.0,
    urlopen_fn: Callable[..., object] = urlopen,
) -> bool:
    """Return True when the observability backend responds successfully."""
    for probe_url in _build_observability_backend_probe_urls(health_url):
        try:
            with urlopen_fn(probe_url, timeout=timeout_seconds) as response:
                status = getattr(response, "status", 200)
                if int(status) < 400:
                    return True
        except (HTTPError, URLError, OSError, ValueError):
            continue
    return False


def _build_backend_base_url(health_url: str) -> str:
    if health_url.endswith("/health"):
        return health_url[: -len("/health")]
    return health_url.rstrip("/")


def probe_observability_backend_required_paths(
    health_url: str,
    *,
    required_probe_paths: tuple[str, ...],
    timeout_seconds: float = 1.0,
    urlopen_fn: Callable[..., object] = urlopen,
) -> bool:
    """Return True when the backend exposes all required HTTP capability paths."""
    if not required_probe_paths:
        return True
    base_url = _build_backend_base_url(health_url)
    for raw_path in required_probe_paths:
        path = raw_path if raw_path.startswith("/") else f"/{raw_path}"
        try:
            with urlopen_fn(f"{base_url}{path}", timeout=timeout_seconds) as response:
                status = getattr(response, "status", 200)
                if int(status) >= 400:
                    return False
        except (HTTPError, URLError, OSError, ValueError):
            return False
    return True


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


def wait_for_observability_backend_required_paths_ready(
    health_url: str,
    *,
    required_probe_paths: tuple[str, ...],
    timeout_seconds: float = DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS,
    probe_timeout_seconds: float = DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PROBE_TIMEOUT_SECONDS,
    poll_seconds: float = DEFAULT_OBSERVABILITY_BACKEND_POLL_SECONDS,
    required_probe_fn: Callable[..., bool] = probe_observability_backend_required_paths,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> bool:
    """Poll backend capability routes until they respond or timeout expires."""
    if not required_probe_paths:
        return True
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if required_probe_fn(
            health_url,
            required_probe_paths=required_probe_paths,
            timeout_seconds=probe_timeout_seconds,
        ):
            return True
        sleep_fn(poll_seconds)
    return required_probe_fn(
        health_url,
        required_probe_paths=required_probe_paths,
        timeout_seconds=probe_timeout_seconds,
    )


def _reuse_observability_backend_if_ready(
    *,
    health_url: str,
    port: int,
    required_probe_paths: tuple[str, ...],
    probe_fn: Callable[..., bool],
    required_probe_fn: Callable[..., bool],
    required_probe_timeout_seconds: float,
    drop_stale_backend_fn: Callable[[int], bool],
    info_printer: Callable[[str], None],
    warning_printer: Callable[[str], None],
) -> ObservabilityBackendEnsureResult | None:
    if not probe_fn(health_url):
        return None
    if required_probe_fn(
        health_url,
        required_probe_paths=required_probe_paths,
        timeout_seconds=required_probe_timeout_seconds,
    ):
        info_printer(f"Observability backend: reusing {health_url}")
        return ObservabilityBackendEnsureResult(
            status="reused",
            health_url=health_url,
            message=f"Observability backend already ready at {health_url}.",
        )
    warning_printer(
        "Observability backend: existing listener is reachable but missing "
        "required audit capabilities; restarting detached Quarantine Explorer backend."
    )
    if drop_stale_backend_fn(port):
        return None
    return ObservabilityBackendEnsureResult(
        status="failed",
        health_url=health_url,
        message=(
            "Existing backend is missing required audit capabilities and "
            f"could not be restarted on port {port}."
        ),
    )


def _read_backend_startup_log_excerpt(
    log_path: Path,
    *,
    max_lines: int = 8,
    max_chars: int = 1200,
) -> str | None:
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    nonempty_lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not nonempty_lines:
        return None
    excerpt = " || ".join(nonempty_lines[-max_lines:])
    if len(excerpt) > max_chars:
        excerpt = f"...{excerpt[-max_chars:]}"
    return excerpt


def _build_startup_failure_detail(
    log_path: Path,
    *,
    process: subprocess.Popen[bytes] | None = None,
) -> str:
    details: list[str] = [f"Startup log: {log_path}."]
    if process is not None and hasattr(process, "poll"):
        exit_code = process.poll()
        if isinstance(exit_code, int):
            details.append(f"Exit code: {exit_code}.")
    excerpt = _read_backend_startup_log_excerpt(log_path)
    if excerpt:
        details.append(f"Tail: {excerpt}")
    return " ".join(details)


def _describe_required_probe_failure(
    health_url: str,
    *,
    required_probe_paths: tuple[str, ...],
    timeout_seconds: float = 1.0,
    urlopen_fn: Callable[..., object] = urlopen,
) -> str | None:
    if not required_probe_paths:
        return None
    base_url = _build_backend_base_url(health_url)
    raw_path = required_probe_paths[0]
    path = raw_path if raw_path.startswith("/") else f"/{raw_path}"
    probe_url = f"{base_url}{path}"
    try:
        with urlopen_fn(probe_url, timeout=timeout_seconds) as response:
            status = int(getattr(response, "status", 200))
            if status < 400:
                return None
            return f"Capability probe {probe_url} returned HTTP {status}."
    except HTTPError as exc:
        body_excerpt = ""
        try:
            raw_body = exc.read().decode("utf-8", errors="replace").strip()
        except OSError:
            raw_body = ""
        if raw_body:
            body_excerpt = f" body={raw_body[:400]!r}"
        return (
            f"Capability probe {probe_url} returned HTTP {exc.code} {exc.reason}."
            f"{body_excerpt}"
        )
    except URLError as exc:
        return f"Capability probe {probe_url} failed: {exc.reason}."
    except OSError as exc:
        return f"Capability probe {probe_url} failed: {exc}."
    except ValueError as exc:
        return f"Capability probe {probe_url} failed: {exc}."


def _start_observability_backend_detached(
    *,
    health_url: str,
    startup_log_path: Path,
    port: int,
    bind_host: str,
    ready_timeout_seconds: float,
    required_probe_timeout_seconds: float,
    poll_seconds: float,
    required_probe_paths: tuple[str, ...],
    probe_fn: Callable[..., bool],
    required_probe_fn: Callable[..., bool],
    start_fn: Callable[..., subprocess.Popen[bytes]],
    wait_fn: Callable[..., bool],
    wait_required_paths_fn: Callable[..., bool],
    info_printer: Callable[[str], None],
    warning_printer: Callable[[str], None],
) -> ObservabilityBackendEnsureResult:
    try:
        process = start_fn(bind_host=bind_host, port=port)
    except OSError as exc:
        startup_detail = _build_startup_failure_detail(startup_log_path)
        warning_printer(
            "Observability backend: failed to start detached Quarantine Explorer "
            f"backend on port {port} ({exc}). {startup_detail} Grafana ID panels "
            "may remain empty."
        )
        return ObservabilityBackendEnsureResult(
            status="failed",
            health_url=health_url,
            message=f"{exc}. {startup_detail}",
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
    if ready and wait_required_paths_fn(
        health_url,
        required_probe_paths=required_probe_paths,
        timeout_seconds=max(
            ready_timeout_seconds,
            DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PATHS_READY_TIMEOUT_SECONDS,
        ),
        probe_timeout_seconds=required_probe_timeout_seconds,
        poll_seconds=poll_seconds,
        required_probe_fn=required_probe_fn,
    ):
        info_printer(f"Observability backend: started {health_url}")
        return ObservabilityBackendEnsureResult(
            status="started",
            health_url=health_url,
            pid=getattr(process, "pid", None),
            command=command,
            message=f"Started detached Quarantine Explorer backend at {health_url}.",
        )

    capability_failure_detail = _describe_required_probe_failure(
        health_url,
        required_probe_paths=required_probe_paths,
        timeout_seconds=required_probe_timeout_seconds,
    )
    startup_detail = _build_startup_failure_detail(
        startup_log_path,
        process=process,
    )
    warning_printer(
        "Observability backend: detached Quarantine Explorer process did not "
        "become ready with required audit capabilities at "
        f"{health_url}. {startup_detail} "
        f"{capability_failure_detail or ''} Grafana ID panels may remain empty."
    )
    return ObservabilityBackendEnsureResult(
        status="failed",
        health_url=health_url,
        pid=getattr(process, "pid", None),
        command=command,
        message=(
            "Detached backend did not become ready with required audit "
            f"capabilities at {health_url}. {startup_detail} "
            f"{capability_failure_detail or ''}"
        ),
    )


def ensure_observability_backend_started(
    *,
    enabled: bool,
    port: int = DEFAULT_HEALTH_SERVER_PORT,
    probe_host: str = DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST,
    bind_host: str = DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST,
    ready_timeout_seconds: float = DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS,
    required_probe_timeout_seconds: float = DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PROBE_TIMEOUT_SECONDS,
    poll_seconds: float = DEFAULT_OBSERVABILITY_BACKEND_POLL_SECONDS,
    required_probe_paths: tuple[str, ...] = (),
    probe_fn: Callable[..., bool] = probe_observability_backend,
    required_probe_fn: Callable[..., bool] = probe_observability_backend_required_paths,
    start_fn: Callable[
        ..., subprocess.Popen[bytes]
    ] = start_detached_quarantine_backend,
    wait_fn: Callable[..., bool] = wait_for_observability_backend_ready,
    wait_required_paths_fn: Callable[
        ..., bool
    ] = wait_for_observability_backend_required_paths_ready,
    drop_stale_backend_fn: Callable[[int], bool] = drop_listening_backend_on_port,
    info_printer: Callable[[str], None] = echo_info,
    warning_printer: Callable[[str], None] = echo_warning,
) -> ObservabilityBackendEnsureResult:
    """Ensure the detached observability backend is running for Grafana panels."""
    health_url = build_observability_backend_health_url(host=probe_host, port=port)
    startup_log_path = build_detached_backend_log_path(port)
    if not enabled:
        return ObservabilityBackendEnsureResult(
            status="disabled",
            health_url=health_url,
            message="Observability backend auto-start disabled by CLI flag.",
        )

    reuse_result = _reuse_observability_backend_if_ready(
        health_url=health_url,
        port=port,
        required_probe_paths=required_probe_paths,
        probe_fn=probe_fn,
        required_probe_fn=required_probe_fn,
        required_probe_timeout_seconds=required_probe_timeout_seconds,
        drop_stale_backend_fn=drop_stale_backend_fn,
        info_printer=info_printer,
        warning_printer=warning_printer,
    )
    if reuse_result is not None:
        return reuse_result

    return _start_observability_backend_detached(
        health_url=health_url,
        startup_log_path=startup_log_path,
        port=port,
        bind_host=bind_host,
        ready_timeout_seconds=ready_timeout_seconds,
        required_probe_timeout_seconds=required_probe_timeout_seconds,
        poll_seconds=poll_seconds,
        required_probe_paths=required_probe_paths,
        probe_fn=probe_fn,
        required_probe_fn=required_probe_fn,
        start_fn=start_fn,
        wait_fn=wait_fn,
        wait_required_paths_fn=wait_required_paths_fn,
        info_printer=info_printer,
        warning_printer=warning_printer,
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


__all__ = [
    "DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST",
    "DEFAULT_OBSERVABILITY_BACKEND_POLL_SECONDS",
    "DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST",
    "DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS",
    "DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PATHS_READY_TIMEOUT_SECONDS",
    "DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PROBE_TIMEOUT_SECONDS",
    "ObservabilityBackendEnsureResult",
    "_build_detached_backend_env",
    "_build_detached_backend_popen_kwargs",
    "_build_observability_backend_probe_urls",
    "build_detached_backend_log_path",
    "build_observability_backend_health_url",
    "ensure_observability_backend_started",
    "probe_observability_backend",
    "probe_observability_backend_required_paths",
    "python_executable_to_tuple",
    "should_disable_transient_health_server",
    "start_detached_quarantine_backend",
    "wait_for_observability_backend_required_paths_ready",
    "wait_for_observability_backend_ready",
]
