"""Prometheus text exposition for the health-server scrape path.

Keeps ``prometheus_client`` imports inside the observability infrastructure
layer so interfaces routing mixins stay free of direct Prometheus coupling.
"""

from __future__ import annotations

__all__ = [
    "HEALTH_SCRAPE_UP_EXPOSITION",
    "build_health_server_metrics_exposition",
]

HEALTH_SCRAPE_UP_EXPOSITION = (
    "# HELP bioetl_health_server_scrape_up Health server /metrics scrape "
    "liveness (1=serving).\n"
    "# TYPE bioetl_health_server_scrape_up gauge\n"
    "bioetl_health_server_scrape_up 1\n"
)


def build_health_server_metrics_exposition() -> str:
    """Build Prometheus text exposition for the health-server scrape path."""
    try:
        from prometheus_client import REGISTRY, generate_latest

        body = generate_latest(REGISTRY).decode("utf-8")
        if not body.strip():
            return HEALTH_SCRAPE_UP_EXPOSITION
        if "bioetl_health_server_scrape_up" not in body:
            body = body.rstrip() + "\n" + HEALTH_SCRAPE_UP_EXPOSITION
        return body if body.endswith("\n") else f"{body}\n"
    except (
        ImportError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ):
        return HEALTH_SCRAPE_UP_EXPOSITION
