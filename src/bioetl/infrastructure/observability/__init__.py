# pyright: reportImportCycles=false
# Import cycle residual (PD4).
# Import cycle residual tracked in allowlist (PD3).
"""Infrastructure layer observability components.

This package contains implementations of observability ports:
- Metrics (Prometheus)
- Tracing (OpenTelemetry - optional)
- Logging (Structlog integration)
- Health Checks

Implements RULES.md §3 (Observability).

For new code, prefer UnifiedLogger which enforces Log Schema (§3.2.1)
with mandatory fields: timestamp, level, run_id, pipeline, stage.

This module intentionally keeps heavyweight adapters lazily loaded. Importing a
light submodule such as ``circuit_breaker_mapping`` should not eagerly pull the
OpenTelemetry SDK and optional host-introspection dependencies at package
import time.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from bioetl.domain.exceptions import MetricsServerError
from bioetl.domain.ports.noop import NoOpMetrics, NoOpTracing

if TYPE_CHECKING:
    from bioetl.infrastructure.observability.logging import StructlogLogger
    from bioetl.infrastructure.observability.metrics_server_adapter import (
        MetricsServerAdapter,
    )
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger
    from bioetl.infrastructure.observability.prometheus_metrics import (
        PrometheusMetrics,
    )
    from bioetl.infrastructure.observability.server import start_metrics_server
    from bioetl.infrastructure.observability.tracing import OpenTelemetryTracer
    from bioetl.infrastructure.observability.unified_logger import (
        UnifiedLogger,
        create_unified_logger,
    )

__all__ = [
    "MetricsServerAdapter",
    "MetricsServerError",
    "NoOpLogger",
    "NoOpMetrics",
    "NoOpTracing",
    "OpenTelemetryTracer",
    "PrometheusMetrics",
    "StructlogLogger",
    "UnifiedLogger",
    "create_unified_logger",
    "start_metrics_server",
]

_EXPORT_MAP: dict[str, tuple[str, str]] = {
    "MetricsServerAdapter": (
        "bioetl.infrastructure.observability.metrics_server_adapter",
        "MetricsServerAdapter",
    ),
    "NoOpLogger": (
        "bioetl.infrastructure.observability.noop_logger",
        "NoOpLogger",
    ),
    "OpenTelemetryTracer": (
        "bioetl.infrastructure.observability.tracing",
        "OpenTelemetryTracer",
    ),
    "PrometheusMetrics": (
        "bioetl.infrastructure.observability.prometheus_metrics",
        "PrometheusMetrics",
    ),
    "StructlogLogger": (
        "bioetl.infrastructure.observability.logging",
        "StructlogLogger",
    ),
    "UnifiedLogger": (
        "bioetl.infrastructure.observability.unified_logger",
        "UnifiedLogger",
    ),
    "create_unified_logger": (
        "bioetl.infrastructure.observability.unified_logger",
        "create_unified_logger",
    ),
    "start_metrics_server": (
        "bioetl.infrastructure.observability.server",
        "start_metrics_server",
    ),
}


def __getattr__(
    name: str,
) -> Any:  # Any: lazy module exports expose heterogeneous adapter types
    """Lazily resolve public re-exports on first access."""
    if TYPE_CHECKING:
        raise AttributeError
    try:
        module_name, attr_name = _EXPORT_MAP[name]
    except KeyError as exc:  # pragma: no cover - normal attribute error path
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return stable package exports for help(), dir(), and shell introspection."""
    return sorted(set(globals()) | set(__all__))
