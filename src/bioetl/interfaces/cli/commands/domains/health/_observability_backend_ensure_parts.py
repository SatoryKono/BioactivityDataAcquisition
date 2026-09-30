"""Small part builders for ``ensure_observability_backend_started``."""

from __future__ import annotations

from bioetl.application.services.ops.observability_backend_startup_types import (
    _DropStaleBackendFn,
    _ListenerPidFn,
    _MessagePrinter,
    _ObservabilityBackendRuntimeHooks,
    _ProbeFn,
    _RequiredProbeFn,
    _StartFn,
    _WaitFn,
    _WaitRequiredPathsFn,
)


def _require_integral_backend_port(raw_port: float) -> None:
    """Reject floats that would be truncated by ``int`` conversion."""
    if not raw_port.is_integer():
        raise TypeError("observability_backend_port must be an integral CLI value")


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
