"""Private startup orchestration for the detached observability backend."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from bioetl.interfaces.cli.commands.domains.health.observability_backend_failure_details import (
    _append_backend_startup_diagnostic,
    _build_startup_failure_detail,
    _describe_required_probe_failure,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_probes import (
    DEFAULT_OBSERVABILITY_BACKEND_POLL_SECONDS,
    DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS,
    DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PATHS_READY_TIMEOUT_SECONDS,
    DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PROBE_TIMEOUT_SECONDS,
    probe_observability_backend,
    probe_observability_backend_required_paths,
    wait_for_observability_backend_ready,
    wait_for_observability_backend_required_paths_ready,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_process import (
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
    from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
        ObservabilityBackendEnsureResult,
    )

DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST = "127.0.0.1"
DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST = "0.0.0.0"


class _StartedBackendProcess(Protocol):
    """Minimal process surface needed after detached backend startup."""

    args: object
    pid: int | None


def _reuse_observability_backend_if_ready(
    *,
    health_url: str,
    port: int,
    required_probe_paths: tuple[str, ...],
    probe_fn: Callable[..., bool],
    required_probe_fn: Callable[..., bool],
    required_probe_timeout_seconds: float,
    drop_stale_backend_fn: Callable[[int], bool],
    listener_pid_fn: Callable[[int], int | None],
    info_printer: Callable[[str], None],
    warning_printer: Callable[[str], None],
    result_factory: Callable[..., ObservabilityBackendEnsureResult],
) -> ObservabilityBackendEnsureResult | None:
    if not probe_fn(health_url):
        existing_pid = listener_pid_fn(port)
        if existing_pid is None:
            return None
        warning_printer(
            "Observability backend: existing listener on port "
            f"{port} (pid={existing_pid}) is bound but health probes timeout; "
            "restarting detached Quarantine Explorer backend."
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
        "required audit capabilities; restarting detached Quarantine Explorer backend."
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
    result_factory: Callable[..., ObservabilityBackendEnsureResult],
    build_startup_failure_detail_fn: Callable[..., str],
    describe_required_probe_failure_fn: Callable[..., str | None],
    append_backend_startup_diagnostic_fn: Callable[..., None],
    python_executable_to_tuple_fn: Callable[[object], tuple[str, ...]],
) -> ObservabilityBackendEnsureResult:
    try:
        process = start_fn(bind_host=bind_host, port=port)
    except OSError as exc:
        startup_detail = build_startup_failure_detail_fn(startup_log_path)
        warning_printer(
            "Observability backend: failed to start detached Quarantine Explorer "
            f"backend on port {port} ({exc}). {startup_detail} Grafana ID panels "
            "may remain empty."
        )
        return result_factory(
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
        python_executable_to_tuple_fn(process.args) if hasattr(process, "args") else ()
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
        return _build_started_backend_result(
            health_url=health_url,
            process=process,
            command=command,
            info_printer=info_printer,
            result_factory=result_factory,
        )

    return _build_backend_capability_failure_result(
        health_url=health_url,
        startup_log_path=startup_log_path,
        process=process,
        command=command,
        required_probe_paths=required_probe_paths,
        required_probe_timeout_seconds=required_probe_timeout_seconds,
        warning_printer=warning_printer,
        result_factory=result_factory,
        build_startup_failure_detail_fn=build_startup_failure_detail_fn,
        describe_required_probe_failure_fn=describe_required_probe_failure_fn,
        append_backend_startup_diagnostic_fn=append_backend_startup_diagnostic_fn,
    )


def _build_started_backend_result(
    *,
    health_url: str,
    process: _StartedBackendProcess,
    command: tuple[str, ...],
    info_printer: Callable[[str], None],
    result_factory: Callable[..., ObservabilityBackendEnsureResult],
) -> ObservabilityBackendEnsureResult:
    info_printer(f"Observability backend: started {health_url}")
    return result_factory(
        status="started",
        health_url=health_url,
        pid=getattr(process, "pid", None),
        command=command,
        message=f"Started detached Quarantine Explorer backend at {health_url}.",
    )


def _build_backend_capability_failure_result(
    *,
    health_url: str,
    startup_log_path: Path,
    process: _StartedBackendProcess,
    command: tuple[str, ...],
    required_probe_paths: tuple[str, ...],
    required_probe_timeout_seconds: float,
    warning_printer: Callable[[str], None],
    result_factory: Callable[..., ObservabilityBackendEnsureResult],
    build_startup_failure_detail_fn: Callable[..., str],
    describe_required_probe_failure_fn: Callable[..., str | None],
    append_backend_startup_diagnostic_fn: Callable[..., None],
) -> ObservabilityBackendEnsureResult:
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
        "Observability backend: detached Quarantine Explorer process did not "
        "become ready with required audit capabilities at "
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


def ensure_observability_backend_started_impl(
    *,
    enabled: bool,
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
    drop_stale_backend_fn: Callable[[int], bool],
    listener_pid_fn: Callable[[int], int | None],
    info_printer: Callable[[str], None],
    warning_printer: Callable[[str], None],
    result_factory: Callable[..., ObservabilityBackendEnsureResult],
    build_startup_failure_detail_fn: Callable[..., str],
    describe_required_probe_failure_fn: Callable[..., str | None],
    append_backend_startup_diagnostic_fn: Callable[..., None],
    python_executable_to_tuple_fn: Callable[[object], tuple[str, ...]],
) -> ObservabilityBackendEnsureResult:
    """Ensure the detached backend is running using runtime-injected patch points."""
    if not enabled:
        return result_factory(
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
        listener_pid_fn=listener_pid_fn,
        info_printer=info_printer,
        warning_printer=warning_printer,
        result_factory=result_factory,
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
        result_factory=result_factory,
        build_startup_failure_detail_fn=build_startup_failure_detail_fn,
        describe_required_probe_failure_fn=describe_required_probe_failure_fn,
        append_backend_startup_diagnostic_fn=append_backend_startup_diagnostic_fn,
        python_executable_to_tuple_fn=python_executable_to_tuple_fn,
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
    listener_pid_fn: Callable[[int], int | None] = find_listening_backend_pid_by_port,
    info_printer: Callable[[str], None] = echo_info,
    warning_printer: Callable[[str], None] = echo_warning,
) -> ObservabilityBackendEnsureResult:
    """Ensure the detached observability backend is running for Grafana panels."""
    from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
        ObservabilityBackendEnsureResult,
        build_observability_backend_health_url,
    )

    return ensure_observability_backend_started_impl(
        enabled=enabled,
        health_url=build_observability_backend_health_url(host=probe_host, port=port),
        startup_log_path=build_detached_backend_log_path(port),
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
        drop_stale_backend_fn=drop_stale_backend_fn,
        listener_pid_fn=listener_pid_fn,
        info_printer=info_printer,
        warning_printer=warning_printer,
        result_factory=ObservabilityBackendEnsureResult,
        build_startup_failure_detail_fn=_build_startup_failure_detail,
        describe_required_probe_failure_fn=_describe_required_probe_failure,
        append_backend_startup_diagnostic_fn=_append_backend_startup_diagnostic,
        python_executable_to_tuple_fn=python_executable_to_tuple,
    )


__all__ = [
    "DEFAULT_OBSERVABILITY_BACKEND_BIND_HOST",
    "DEFAULT_OBSERVABILITY_BACKEND_PROBE_HOST",
    "ensure_observability_backend_started",
    "ensure_observability_backend_started_impl",
]
