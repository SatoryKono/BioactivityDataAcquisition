"""HTTP interface types for BioETL."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from bioetl.domain.types import JsonDict


@dataclass
class HealthResponse:
    """Health check response data."""

    status: str
    timestamp: str
    version: str = "1.0.0"
    checks: JsonDict = field(  # Any: CLI/HTTP response values are heterogeneous
        default_factory=dict
    )  # Any: CLI/HTTP response values are heterogeneous

    def to_json(self) -> str:
        """Convert to JSON string.

        Returns:
            JSON string representation.
        """
        return json.dumps(
            {
                "status": self.status,
                "timestamp": self.timestamp,
                "version": self.version,
                "checks": self.checks,
            },
            indent=2,
        )

    @property
    def http_status(self) -> int:
        """Return HTTP status code based on health status."""
        if self.status in {"healthy", "degraded"}:
            return 200  # Still operational
        return 503  # Service Unavailable


__all__ = ["HealthResponse"]


# Pure liveness fallback when no exposition adapter is injected (unit tests).
_DEFAULT_HEALTH_SCRAPE_UP_EXPOSITION = (
    "# HELP bioetl_health_server_scrape_up Health server /metrics scrape "
    "liveness (1=serving).\n"
    "# TYPE bioetl_health_server_scrape_up gauge\n"
    "bioetl_health_server_scrape_up 1\n"
)


class _StaticHealthMetricsExposition:
    """Interfaces-local fallback exposition (no infrastructure import)."""

    def build_exposition(self) -> str:
        return _DEFAULT_HEALTH_SCRAPE_UP_EXPOSITION
