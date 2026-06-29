"""Runtime helpers for self-managed observability backend startup."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

from bioetl.interfaces.cli.commands.domains.health.observability_backend_failure_details import (
    _build_startup_failure_detail,
    _describe_required_probe_failure,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_failure_details import (
    _read_backend_startup_log_excerpt as _read_backend_startup_log_excerpt,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_probes import (
    DEFAULT_OBSERVABILITY_BACKEND_POLL_SECONDS,
    DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS,
    DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PATHS_READY_TIMEOUT_SECONDS,
    DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PROBE_TIMEOUT_SECONDS,
    _build_observability_backend_probe_urls,
    probe_observability_backend,
    probe_observability_backend_required_paths,
    wait_for_observability_backend_ready,
    wait_for_observability_backend_required_paths_ready,
)
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


class _StartedBackendProcess(Protocol):
    """Minimal process surface needed after detached backend startup."""

    args: object
    pid: int | None


class _ObservabilityBackendCliInput(Protocol):
    """Minimal dataclass-like CLI payload supporting backend attachment."""

    ensure_observability_backend: bool
    observability_backend_port: int
    health_server: bool
    health_port: int


DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST = "127.0.0.1"
DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST = "0.0.0.0"
_SELECTOR_CATALOG_PROBE_PATH = (
    "/ops/control-plane/filter-options?dimension=pipeline&response_shape=list"
)

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


def build_observability_backend_required_probe_paths(
    *,
    pipelines: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """Build capability probe paths that prove control-plane observability works."""
    normalized_pipelines = tuple(
        sorted({pipeline.strip() for pipeline in pipelines if pipeline.strip()})
    )
    paths = [_SELECTOR_CATALOG_PROBE_PATH]
    for pipeline in normalized_pipelines:
        encoded_pipeline = quote(pipeline, safe="_-.")
        paths.append(
            f"/ops/control-plane/checkpoint-freshness?pipeline={encoded_pipeline}"
        )
    return tuple(paths)


def resolve_observability_backend_cli_options(
    options: Mapping[str, object],
    *,
    default_port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> tuple[bool, int]:
    """Read backend auto-start options from raw Click kwargs mapping."""
    return (
        bool(options.get("ensure_observability_backend", True)),
        int(options.get("observability_backend_port", default_port)),
    )


def build_observability_backend_cli_kwargs(
    *,
    ensure_observability_backend: bool,
    observability_backend_port: int,
) -> dict[str, object]:
    """Return normalized CLI kwargs shared by run-oriented command inputs."""
    return {
        "ensure_observability_backend": ensure_observability_backend,
        "observability_backend_port": observability_backend_port,
    }


def build_observability_backend_cli_kwargs_from_options(
    options: Mapping[str, object],
    *,
    default_port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> dict[str, object]:
    """Resolve and normalize backend startup kwargs from raw Click options."""
    ensure_observability_backend, observability_backend_port = (
        resolve_observability_backend_cli_options(
            options,
            default_port=default_port,
        )
    )
    return build_observability_backend_cli_kwargs(
        ensure_observability_backend=ensure_observability_backend,
        observability_backend_port=observability_backend_port,
    )


def attach_observability_backend_to_cli_input(
    cli_input: _ObservabilityBackendCliInput,
    *,
    required_probe_paths: tuple[str, ...],
    ensure_backend_started_fn: Callable[
        ..., ObservabilityBackendEnsureResult
    ] | None = None,
    disable_transient_health_server_fn: Callable[..., bool] | None = None,
) -> _ObservabilityBackendCliInput:
    """Ensure backend startup and disable the transient health server when replaced."""
    ensure_backend_started = (
        ensure_backend_started_fn or ensure_observability_backend_started
    )
    disable_transient_health_server = (
        disable_transient_health_server_fn or should_disable_transient_health_server
    )
    backend_result = ensure_backend_started(
        enabled=cli_input.ensure_observability_backend,
        port=cli_input.observability_backend_port,
        required_probe_paths=required_probe_paths,
    )
    if disable_transient_health_server(
        health_server_enabled=cli_input.health_server,
        health_port=cli_input.health_port,
        observability_backend_port=cli_input.observability_backend_port,
        backend_result=backend_result,
    ):
        return replace(cli_input, health_server=False)
    return cli_input


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
    start_fn: Callable[..., _StartedBackendProcess],
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
    start_fn: Callable[..., _StartedBackendProcess] = start_detached_quarantine_backend,
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
    "attach_observability_backend_to_cli_input",
    "build_detached_backend_log_path",
    "build_observability_backend_cli_kwargs",
    "build_observability_backend_health_url",
    "build_observability_backend_required_probe_paths",
    "ensure_observability_backend_started",
    "probe_observability_backend",
    "probe_observability_backend_required_paths",
    "python_executable_to_tuple",
    "resolve_observability_backend_cli_options",
    "should_disable_transient_health_server",
    "start_detached_quarantine_backend",
    "wait_for_observability_backend_ready",
    "wait_for_observability_backend_required_paths_ready",
]
