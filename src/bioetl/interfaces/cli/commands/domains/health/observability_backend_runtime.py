"""Runtime helpers for self-managed observability backend startup."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Protocol

from bioetl.interfaces.cli.commands.domains.health._observability_backend_startup import (
    _STARTUP_DETACHED_HOOK_KEYS,
    _STARTUP_DETACHED_KEYS,
    ensure_observability_backend_started_impl,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_failure_details import (
    _append_backend_startup_diagnostic,
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
    find_listening_backend_pid_by_port,
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
_CONTROL_PLANE_READY_PROBE_PATH = "/ops/control-plane/ready"

_DETACHED_STATUS = frozenset({"reused", "started"})
_STARTUP_KWARG_KEYS = ("enabled", *_STARTUP_DETACHED_KEYS)
_RUNTIME_HOOK_KEYS = (
    *_STARTUP_DETACHED_HOOK_KEYS,
    "drop_stale_backend_fn",
    "listener_pid_fn",
)


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
    del pipelines
    return (_CONTROL_PLANE_READY_PROBE_PATH,)


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
    ensure_backend_started_fn: Callable[..., ObservabilityBackendEnsureResult]
    | None = None,
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


def _observability_backend_startup_kwargs(
    *,
    enabled: bool,
    port: int,
    probe_host: str,
    bind_host: str,
    ready_timeout_seconds: float,
    required_probe_timeout_seconds: float,
    poll_seconds: float,
    required_probe_paths: tuple[str, ...],
) -> dict[str, object]:
    values = (
        enabled,
        build_observability_backend_health_url(host=probe_host, port=port),
        build_detached_backend_log_path(port),
        port,
        bind_host,
        ready_timeout_seconds,
        required_probe_timeout_seconds,
        poll_seconds,
        required_probe_paths,
    )
    return dict(zip(_STARTUP_KWARG_KEYS, values, strict=True))


def _observability_backend_runtime_hooks(
    *,
    probe_fn: Callable[..., bool],
    required_probe_fn: Callable[..., bool],
    start_fn: Callable[..., _StartedBackendProcess],
    wait_fn: Callable[..., bool],
    wait_required_paths_fn: Callable[..., bool],
    drop_stale_backend_fn: Callable[[int], bool],
    listener_pid_fn: Callable[[int], int | None],
    info_printer: Callable[[str], None],
    warning_printer: Callable[[str], None],
) -> dict[str, Callable[..., object]]:
    values: tuple[Callable[..., object], ...] = (
        probe_fn,
        required_probe_fn,
        start_fn,
        wait_fn,
        wait_required_paths_fn,
        info_printer,
        warning_printer,
        drop_stale_backend_fn,
        listener_pid_fn,
    )
    return dict(zip(_RUNTIME_HOOK_KEYS, values, strict=True))


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
    listener_pid_fn: Callable[[int], int | None] = find_listening_backend_pid_by_port,
    info_printer: Callable[[str], None] = echo_info,
    warning_printer: Callable[[str], None] = echo_warning,
) -> ObservabilityBackendEnsureResult:
    """Ensure the detached backend is running with runtime-local patch points."""
    runtime_hooks = _observability_backend_runtime_hooks(
        probe_fn=probe_fn,
        required_probe_fn=required_probe_fn,
        start_fn=start_fn,
        wait_fn=wait_fn,
        wait_required_paths_fn=wait_required_paths_fn,
        drop_stale_backend_fn=drop_stale_backend_fn,
        listener_pid_fn=listener_pid_fn,
        info_printer=info_printer,
        warning_printer=warning_printer,
    )
    return ensure_observability_backend_started_impl(
        startup_kwargs=_observability_backend_startup_kwargs(
            enabled=enabled,
            port=port,
            probe_host=probe_host,
            bind_host=bind_host,
            ready_timeout_seconds=ready_timeout_seconds,
            required_probe_timeout_seconds=required_probe_timeout_seconds,
            poll_seconds=poll_seconds,
            required_probe_paths=required_probe_paths,
        ),
        runtime_hooks=runtime_hooks,
        failure_handlers=_observability_backend_failure_kwargs(),
        result_factory=ObservabilityBackendEnsureResult,
    )


def _observability_backend_failure_kwargs() -> dict[str, Callable[..., object]]:
    return {
        "build_startup_failure_detail_fn": _build_startup_failure_detail,
        "describe_required_probe_failure_fn": _describe_required_probe_failure,
        "append_backend_startup_diagnostic_fn": _append_backend_startup_diagnostic,
        "python_executable_to_tuple_fn": python_executable_to_tuple,
    }


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
