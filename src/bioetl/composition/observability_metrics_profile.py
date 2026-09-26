"""Operator-facing metrics/admin profile for the observability runtime seam."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlunsplit

from bioetl.composition import _services
from bioetl.composition.runtime_builders import config_access as _config_access
from bioetl.domain.runtime.composition_boundary_policy import (
    resolve_metrics_publication_modes,
)

_PUSHGATEWAY_FALLBACK = "localhost:9091"


@dataclass(frozen=True, slots=True)
class MetricsOperatorProfile:
    """Operator-facing summary of metrics/admin observability behavior."""

    metrics_enabled: bool
    metrics_server_enabled: bool
    metrics_server_running: bool
    metrics_port: int
    metrics_addr: str
    metrics_started_at: datetime | None
    metrics_endpoint: str | None
    metrics_server_mode: str
    pushgateway_mode: str
    pushgateway_gateway: str
    tracing_enabled: bool
    audit_enabled: bool

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe diagnostics payload."""
        return {
            "metrics_enabled": self.metrics_enabled,
            "metrics_server_enabled": self.metrics_server_enabled,
            "metrics_server_running": self.metrics_server_running,
            "metrics_port": self.metrics_port,
            "metrics_addr": self.metrics_addr,
            "metrics_started_at": (
                self.metrics_started_at.isoformat()
                if self.metrics_started_at is not None
                else None
            ),
            "metrics_endpoint": self.metrics_endpoint,
            "metrics_server_mode": self.metrics_server_mode,
            "pushgateway_mode": self.pushgateway_mode,
            "pushgateway_gateway": self.pushgateway_gateway,
            "tracing_enabled": self.tracing_enabled,
            "audit_enabled": self.audit_enabled,
        }


def get_metrics_operator_profile() -> MetricsOperatorProfile:
    """Return the canonical operator-facing metrics/admin profile."""

    settings = _config_access.get_settings()
    metrics_service = _services.get_metrics_service()
    status = metrics_service.get_status()
    live_metrics_port = (
        status.port
        if status.running and status.port is not None
        else settings.metrics_port
    )
    metrics_enabled = bool(settings.observability.metrics_enabled)
    metrics_server_enabled = bool(settings.observability.metrics_server_enabled)
    metrics_endpoint = None
    if metrics_enabled and metrics_server_enabled:
        metrics_endpoint = urlunsplit(
            (
                "http",
                f"{settings.metrics_addr}:{live_metrics_port}",
                "/metrics",
                "",
                "",
            )
        )
    metrics_server_mode, pushgateway_mode = resolve_metrics_publication_modes(
        metrics_enabled=metrics_enabled,
        metrics_server_enabled=metrics_server_enabled,
    )
    pushgateway_gateway = (
        getattr(settings, "pushgateway_url", None) or _PUSHGATEWAY_FALLBACK
    )
    return MetricsOperatorProfile(
        metrics_enabled=metrics_enabled,
        metrics_server_enabled=metrics_server_enabled,
        metrics_server_running=status.running,
        metrics_port=live_metrics_port,
        metrics_addr=settings.metrics_addr,
        metrics_started_at=status.started_at,
        metrics_endpoint=metrics_endpoint,
        metrics_server_mode=metrics_server_mode,
        pushgateway_mode=pushgateway_mode,
        pushgateway_gateway=pushgateway_gateway,
        tracing_enabled=bool(settings.observability.tracing_enabled),
        audit_enabled=bool(settings.observability.audit_enabled),
    )
