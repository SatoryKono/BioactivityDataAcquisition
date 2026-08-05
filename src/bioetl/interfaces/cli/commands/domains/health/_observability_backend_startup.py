# Boundary object/payload typing residual at this module.
"""Private startup orchestration for the detached observability backend."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from bioetl.interfaces.cli.commands.domains.health._observability_backend_startup_types import (
    _AppendBackendStartupDiagnosticFn,
    _BackendResultConstructor,
    _BuildStartupFailureDetailFn,
    _DescribeRequiredProbeFailureFn,
    _DropStaleBackendFn,
    _ListenerPidFn,
    _MessagePrinter,
    _ObservabilityBackendFailureHandlers,
    _ObservabilityBackendRuntimeHooks,
    _ObservabilityBackendStartupKwargs,
    _ProbeFn,
    _RequiredProbeFn,
    _StartedBackendProcess,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_probes import (
    DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PATHS_READY_TIMEOUT_SECONDS,
)

DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST = "127.0.0.1"
DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST = "0.0.0.0"


def _reuse_observability_backend_if_ready[ResultT](
    *,
    health_url: str,
    port: int,
    required_probe_paths: tuple[str, ...],
    probe_fn: _ProbeFn,
    required_probe_fn: _RequiredProbeFn,
    required_probe_timeout_seconds: float,
    drop_stale_backend_fn: _DropStaleBackendFn,
    listener_pid_fn: _ListenerPidFn,
    info_printer: _MessagePrinter,
    warning_printer: _MessagePrinter,
    result_factory: _BackendResultConstructor[ResultT],
) -> ResultT | None:
    if not probe_fn(health_url):
        existing_pid = listener_pid_fn(port)
        if existing_pid is None:
            return None
        warning_printer(
            "Observability backend: existing listener on port "
            f"{port} (pid={existing_pid}) is bound but health probes timeout; "
            "restarting detached BioETL Ops HTTP (health server) backend."
        )
        if drop_stale_backend_fn(port):
            return None
        return result_factory(
            status="failed",
            health_url=health_url,
            message=(
                "Existing backend listener "
                f"(pid={existing_pid}) is bound on port {port} but health probes "
                "timeout and the stale process could not be restarted."
            ),
        )
    if required_probe_fn(
        health_url,
        required_probe_paths=required_probe_paths,
        timeout_seconds=required_probe_timeout_seconds,
    ):
        info_printer(f"Observability backend: reusing {health_url}")
        return result_factory(
            status="reused",
            health_url=health_url,
            message=f"Observability backend already ready at {health_url}.",
        )
    warning_printer(
        "Observability backend: existing listener is reachable but missing "
        "required audit capabilities; restarting detached BioETL Ops HTTP "
        "(health server) backend."
    )
    if drop_stale_backend_fn(port):
        return None
    return result_factory(
        status="failed",
        health_url=health_url,
        message=(
            "Existing backend is missing required audit capabilities and "
            f"could not be restarted on port {port}."
        ),
    )


def _start_observability_backend_detached[ResultT](
    *,
    health_url: str,
    startup_log_path: Path,
    port: int,
    bind_host: str,
    timing: tuple[float, float, float],
    required_probe_paths: tuple[str, ...],
    hooks: Mapping[str, object],
    result_factory: _BackendResultConstructor[ResultT],
) -> ResultT:
    """Start a detached backend and wait for capability probes.

    ``timing`` packs ``(ready_timeout, required_probe_timeout, poll_seconds)``.
    ``hooks`` is the runtime-hook mapping (probe/start/wait/print/diagnostics).
    """
    ready_timeout_seconds, required_probe_timeout_seconds, poll_seconds = timing
    probe_fn = hooks["probe_fn"]
    required_probe_fn = hooks["required_probe_fn"]
    start_fn = hooks["start_fn"]
    wait_fn = hooks["wait_fn"]
    wait_required_paths_fn = hooks["wait_required_paths_fn"]
    info_printer = hooks["info_printer"]
    warning_printer = hooks["warning_printer"]
    build_startup_failure_detail_fn = hooks["build_startup_failure_detail_fn"]
    describe_required_probe_failure_fn = hooks["describe_required_probe_failure_fn"]
    append_backend_startup_diagnostic_fn = hooks["append_backend_startup_diagnostic_fn"]
    python_executable_to_tuple_fn = hooks["python_executable_to_tuple_fn"]
    try:
        process = start_fn(bind_host=bind_host, port=port)  # type: ignore[operator]  # pyright: ignore[reportCallIssue]
    except OSError as exc:
        startup_detail = build_startup_failure_detail_fn(startup_log_path)  # type: ignore[operator]  # pyright: ignore[reportCallIssue]
        warning_printer(  # type: ignore[operator]  # pyright: ignore[reportCallIssue]
            "Observability backend: failed to start detached BioETL Ops HTTP "
            f"(health server) backend on port {port} ({exc}). {startup_detail} "
            "Grafana ID panels may remain empty."
        )
        return result_factory(
            status="failed",
            health_url=health_url,
            message=f"{exc}. {startup_detail}",
        )

    ready = wait_fn(  # type: ignore[operator]  # pyright: ignore[reportCallIssue]
        health_url,
        timeout_seconds=ready_timeout_seconds,
        poll_seconds=poll_seconds,
        probe_fn=probe_fn,
    )
    command = (
        python_executable_to_tuple_fn(process.args)  # type: ignore[operator]  # pyright: ignore[reportCallIssue]
        if hasattr(process, "args")
        else ()
    )
    if ready and wait_required_paths_fn(  # type: ignore[operator]  # pyright: ignore[reportCallIssue]
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
        return _build_started_backend_result(
            health_url=health_url,
            process=process,
            command=command,
            info_printer=info_printer,  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
            result_factory=result_factory,
        )

    return _build_backend_capability_failure_result(
        health_url=health_url,
        startup_log_path=startup_log_path,
        process=process,
        command=command,
        required_probe_paths=required_probe_paths,
        required_probe_timeout_seconds=required_probe_timeout_seconds,
        warning_printer=warning_printer,  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        result_factory=result_factory,
        build_startup_failure_detail_fn=build_startup_failure_detail_fn,  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        describe_required_probe_failure_fn=describe_required_probe_failure_fn,  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
        append_backend_startup_diagnostic_fn=append_backend_startup_diagnostic_fn,  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
    )


def _build_started_backend_result[ResultT](
    *,
    health_url: str,
    process: _StartedBackendProcess,
    command: tuple[str, ...],
    info_printer: _MessagePrinter,
    result_factory: _BackendResultConstructor[ResultT],
) -> ResultT:
    info_printer(f"Observability backend: started {health_url}")
    return result_factory(
        status="started",
        health_url=health_url,
        pid=getattr(process, "pid", None),
        command=command,
        message=f"Started detached BioETL Ops HTTP (health server) at {health_url}.",
    )


def _build_backend_capability_failure_result[ResultT](
    *,
    health_url: str,
    startup_log_path: Path,
    process: _StartedBackendProcess,
    command: tuple[str, ...],
    required_probe_paths: tuple[str, ...],
    required_probe_timeout_seconds: float,
    warning_printer: _MessagePrinter,
    result_factory: _BackendResultConstructor[ResultT],
    build_startup_failure_detail_fn: _BuildStartupFailureDetailFn,
    describe_required_probe_failure_fn: _DescribeRequiredProbeFailureFn,
    append_backend_startup_diagnostic_fn: _AppendBackendStartupDiagnosticFn,
) -> ResultT:
    capability_failure_detail = describe_required_probe_failure_fn(
        health_url,
        required_probe_paths=required_probe_paths,
        timeout_seconds=required_probe_timeout_seconds,
    )
    append_backend_startup_diagnostic_fn(
        startup_log_path,
        parent_pid=os.getpid(),
        child_pid=getattr(process, "pid", None),
        command=command,
        diagnostic_lines=(
            f"health_url={health_url}",
            f"required_probe_paths={required_probe_paths!r}",
            capability_failure_detail or "capability_failure=<unknown>",
        ),
    )
    startup_detail = build_startup_failure_detail_fn(startup_log_path, process=process)
    warning_printer(
        "Observability backend: detached BioETL Ops HTTP (health server) process "
        "did not become ready with required audit capabilities at "
        f"{health_url}. {startup_detail} "
        f"{capability_failure_detail or ''} Grafana ID panels may remain empty."
    )
    return result_factory(
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


def ensure_observability_backend_started_impl[ResultT](
    *,
    startup_kwargs: _ObservabilityBackendStartupKwargs,
    runtime_hooks: _ObservabilityBackendRuntimeHooks,
    failure_handlers: _ObservabilityBackendFailureHandlers,
    result_factory: _BackendResultConstructor[ResultT],
) -> ResultT:
    """Ensure the detached backend is running using runtime-injected patch points."""
    enabled = startup_kwargs["enabled"]
    health_url = startup_kwargs["health_url"]
    if not enabled:
        return result_factory(
            status="disabled",
            health_url=health_url,
            message="Observability backend auto-start disabled by CLI flag.",
        )

    reuse_result = _reuse_observability_backend_if_ready(
        health_url=health_url,
        port=startup_kwargs["port"],
        required_probe_paths=startup_kwargs["required_probe_paths"],
        probe_fn=runtime_hooks["probe_fn"],
        required_probe_fn=runtime_hooks["required_probe_fn"],
        required_probe_timeout_seconds=startup_kwargs["required_probe_timeout_seconds"],
        drop_stale_backend_fn=runtime_hooks["drop_stale_backend_fn"],
        listener_pid_fn=runtime_hooks["listener_pid_fn"],
        info_printer=runtime_hooks["info_printer"],
        warning_printer=runtime_hooks["warning_printer"],
        result_factory=result_factory,
    )
    if reuse_result is not None:
        return reuse_result

    return _start_observability_backend_detached(
        health_url=startup_kwargs["health_url"],
        startup_log_path=startup_kwargs["startup_log_path"],
        port=startup_kwargs["port"],
        bind_host=startup_kwargs["bind_host"],
        timing=(
            startup_kwargs["ready_timeout_seconds"],
            startup_kwargs["required_probe_timeout_seconds"],
            startup_kwargs["poll_seconds"],
        ),
        required_probe_paths=startup_kwargs["required_probe_paths"],
        hooks={
            **runtime_hooks,
            **failure_handlers,
        },
        result_factory=result_factory,
    )


__all__ = [
    "DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST",
    "DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST",
    "ensure_observability_backend_started_impl",
]
