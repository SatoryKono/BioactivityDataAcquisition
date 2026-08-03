"""In-process Prometheus metrics server runtime state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock

from bioetl.domain.ports import MetricsServerRuntimeStatus

__all__ = [
    "_SERVER_RUNTIME",
    "_MetricsServerRuntimeState",
    "get_metrics_server_runtime_status",
    "is_metrics_server_running",
    "mark_metrics_server_started",
    "reset_server_state",
]


@dataclass(slots=True)
class _MetricsServerRuntimeState:
    """Process-local metrics server bookkeeping."""

    started: bool = False
    port: int | None = None
    addr: str | None = None
    started_at: datetime | None = None
    lock: Lock = field(default_factory=Lock)


_SERVER_RUNTIME = _MetricsServerRuntimeState()


def mark_metrics_server_started(
    *,
    port: int,
    addr: str,
    started_at: datetime | None,
) -> None:
    """Record a successful in-process metrics server startup."""
    _SERVER_RUNTIME.started = True
    _SERVER_RUNTIME.port = port
    _SERVER_RUNTIME.addr = addr
    _SERVER_RUNTIME.started_at = started_at


def is_metrics_server_running() -> bool:
    """Return the live in-process metrics server state."""
    return _SERVER_RUNTIME.started


def get_metrics_server_runtime_status() -> MetricsServerRuntimeStatus:
    """Return live in-process metrics server runtime metadata."""
    return MetricsServerRuntimeStatus(
        running=_SERVER_RUNTIME.started,
        port=_SERVER_RUNTIME.port if _SERVER_RUNTIME.started else None,
        addr=_SERVER_RUNTIME.addr if _SERVER_RUNTIME.started else None,
        started_at=_SERVER_RUNTIME.started_at if _SERVER_RUNTIME.started else None,
    )


def reset_server_state() -> None:
    """Reset server state for testing purposes only."""
    with _SERVER_RUNTIME.lock:
        _SERVER_RUNTIME.started = False
        _SERVER_RUNTIME.port = None
        _SERVER_RUNTIME.addr = None
        _SERVER_RUNTIME.started_at = None
