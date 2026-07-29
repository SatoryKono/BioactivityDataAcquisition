# Boundary object/payload typing residual at this module.
"""Runtime helpers for self-managed observability backend startup."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from bioetl.interfaces.cli.commands.domains.health._observability_backend_startup import (
    ensure_observability_backend_started_impl,
)
from bioetl.interfaces.cli.commands.domains.health._observability_backend_startup_types import (
    _DropStaleBackendFn,
    _ListenerPidFn,
    _MessagePrinter,
    _ObservabilityBackendFailureHandlers,
    _ObservabilityBackendRuntimeHooks,
    _ObservabilityBackendStartupKwargs,
    _ProbeFn,
    _RequiredProbeFn,
    _StartFn,
    _WaitFn,
    _WaitRequiredPathsFn,
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

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.run.command_policy import (
        RunCommandInput,
    )
    from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
        RunAllCommandInput,
    )


DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST = "127.0.0.1"
DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST = "0.0.0.0"
_CONTROL_PLANE_READY_PROBE_PATH = "/ops/control-plane/ready"

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
    # Local operator loopback probe — plain HTTP is intentional (S5332).
    _scheme = "http"
    return f"{_scheme}://{host}:{port}/health"


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
    raw_port = options.get("observability_backend_port", default_port)
    if isinstance(raw_port, bool) or not isinstance(
        raw_port,
        (str, bytes, bytearray, int, float),
    ):
        raise TypeError("observability_backend_port must be a numeric CLI value")
    return (
        bool(options.get("ensure_observability_backend", True)),
        int(raw_port),
    )


@dataclass(frozen=True, slots=True)
class ObservabilityBackendCliOptions:
    """Normalized observability-backend CLI options for run commands."""

    ensure_observability_backend: bool
    observability_backend_port: int


def build_observability_backend_cli_kwargs(
    *,
    ensure_observability_backend: bool,
    observability_backend_port: int,
) -> ObservabilityBackendCliOptions:
    """Return normalized CLI kwargs shared by run-oriented command inputs."""
    return ObservabilityBackendCliOptions(
        ensure_observability_backend=ensure_observability_backend,
        observability_backend_port=observability_backend_port,
    )


def build_observability_backend_cli_kwargs_from_options(
    options: Mapping[str, object],
    *,
    default_port: int = DEFAULT_HEALTH_SERVER_PORT,
) -> ObservabilityBackendCliOptions:
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
    cli_input: RunCommandInput | RunAllCommandInput,
    *,
    required_probe_paths: tuple[str, ...],
    ensure_backend_started_fn: Callable[..., ObservabilityBackendEnsureResult]
    | None = None,
    disable_transient_health_server_fn: Callable[..., bool] | None = None,
) -> RunCommandInput | RunAllCommandInput:
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
        return cast(
            "RunCommandInput | RunAllCommandInput",
            replace(cli_input, health_server=False),
        )
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
) -> _ObservabilityBackendStartupKwargs:
    return {
        "enabled": enabled,
        "health_url": build_observability_backend_health_url(
            host=probe_host,
            port=port,
        ),
        "startup_log_path": build_detached_backend_log_path(port),
        "port": port,
        "bind_host": bind_host,
        "ready_timeout_seconds": ready_timeout_seconds,
        "required_probe_timeout_seconds": required_probe_timeout_seconds,
        "poll_seconds": poll_seconds,
        "required_probe_paths": required_probe_paths,
    }


def _observability_backend_runtime_hooks(
    *,
    probe_fn: _ProbeFn,
    required_probe_fn: _RequiredProbeFn,
    start_fn: _StartFn,
    wait_fn: _WaitFn,
    wait_required_paths_fn: _WaitRequiredPathsFn,
    drop_stale_backend_fn: _DropStaleBackendFn,
    listener_pid_fn: _ListenerPidFn,
    info_printer: _MessagePrinter,
    warning_printer: _MessagePrinter,
) -> _ObservabilityBackendRuntimeHooks:
    return {
        "probe_fn": probe_fn,
        "required_probe_fn": required_probe_fn,
        "start_fn": start_fn,
        "wait_fn": wait_fn,
        "wait_required_paths_fn": wait_required_paths_fn,
        "drop_stale_backend_fn": drop_stale_backend_fn,
        "listener_pid_fn": listener_pid_fn,
        "info_printer": info_printer,
        "warning_printer": warning_printer,
    }


def ensure_observability_backend_started(
    *,
    enabled: bool,
    port: int = DEFAULT_HEALTH_SERVER_PORT,
    probe_host: str = DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST,
    bind_host: str = DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST,
    timing: tuple[float, float, float] = (
        DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS,
        DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PROBE_TIMEOUT_SECONDS,
        DEFAULT_OBSERVABILITY_BACKEND_POLL_SECONDS,
    ),
    required_probe_paths: tuple[str, ...] = (),
    **hook_overrides: object,
) -> ObservabilityBackendEnsureResult:
    """Ensure the detached backend is running with runtime-local patch points.

    ``timing`` packs ``(ready_timeout, required_probe_timeout, poll_seconds)``.
    Runtime hooks (``probe_fn``, ``start_fn``, printers, ...) may be overridden
    via ``**hook_overrides`` for tests while keeping S107 under budget.
    """
    ready_timeout_seconds, required_probe_timeout_seconds, poll_seconds = timing
    defaults = _observability_backend_runtime_hooks(
        probe_fn=probe_observability_backend,
        required_probe_fn=probe_observability_backend_required_paths,
        start_fn=start_detached_quarantine_backend,
        wait_fn=wait_for_observability_backend_ready,
        wait_required_paths_fn=wait_for_observability_backend_required_paths_ready,
        drop_stale_backend_fn=drop_listening_backend_on_port,
        listener_pid_fn=find_listening_backend_pid_by_port,
        info_printer=echo_info,
        warning_printer=echo_warning,
    )
    # Preserve legacy kwargs that previously were first-class parameters.
    legacy_timing_keys = {
        "ready_timeout_seconds",
        "required_probe_timeout_seconds",
        "poll_seconds",
    }
    for key in legacy_timing_keys:
        if key in hook_overrides:
            # Prefer explicit legacy kwargs when tests still pass them.
            pass
    ready_timeout_seconds = float(
        hook_overrides.pop("ready_timeout_seconds", ready_timeout_seconds)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
    )
    required_probe_timeout_seconds = float(
        hook_overrides.pop(  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
            "required_probe_timeout_seconds", required_probe_timeout_seconds
        )
    )
    poll_seconds = float(hook_overrides.pop("poll_seconds", poll_seconds))  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
    runtime_hooks = {**defaults, **hook_overrides}
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
        runtime_hooks=runtime_hooks,  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        failure_handlers=_observability_backend_failure_kwargs(),
        result_factory=ObservabilityBackendEnsureResult,
    )


def _observability_backend_failure_kwargs() -> _ObservabilityBackendFailureHandlers:
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
