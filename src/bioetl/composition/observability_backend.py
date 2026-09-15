"""Composition-owned wiring for the detached observability backend.

Infrastructure process/HTTP adapters are assembled here so interface adapters
and application use-cases do not import concrete I/O modules.
"""

from __future__ import annotations

from bioetl.infrastructure.observability.observability_backend_process import (
    _build_detached_backend_env,
    _build_detached_backend_popen_kwargs,
    build_detached_backend_log_path,
    drop_listening_backend_on_port,
    find_listening_backend_pid_by_port,
    python_executable_to_tuple,
    start_detached_ops_http_backend,
    start_detached_quarantine_backend,
)
from bioetl.infrastructure.observability.observability_backend_probes import (
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

__all__ = [
    "DEFAULT_OBSERVABILITY_BACKEND_POLL_SECONDS",
    "DEFAULT_OBSERVABILITY_BACKEND_READY_TIMEOUT_SECONDS",
    "DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PATHS_READY_TIMEOUT_SECONDS",
    "DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PROBE_TIMEOUT_SECONDS",
    "_build_detached_backend_env",
    "_build_detached_backend_popen_kwargs",
    "_build_observability_backend_probe_urls",
    "build_detached_backend_log_path",
    "drop_listening_backend_on_port",
    "find_listening_backend_pid_by_port",
    "probe_observability_backend",
    "probe_observability_backend_required_paths",
    "python_executable_to_tuple",
    "start_detached_ops_http_backend",
    "start_detached_quarantine_backend",
    "wait_for_observability_backend_ready",
    "wait_for_observability_backend_required_paths_ready",
]
