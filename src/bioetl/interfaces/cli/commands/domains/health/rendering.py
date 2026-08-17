"""Pure rendering helpers for health CLI commands."""

from __future__ import annotations

import json
from collections.abc import Mapping

__all__ = [
    "all_health_results_healthy",
    "build_health_result_lines",
    "build_health_server_info_lines",
    "render_health_results_json",
]

HealthResultValue = str | float | int | None
HealthResults = Mapping[str, Mapping[str, HealthResultValue]]


def build_health_server_info_lines(host: str, port: int) -> list[str]:
    """Build startup lines for the health server command."""
    return [
        f"Starting health server on http://{host}:{port}",
        "Endpoints:",
        f"  - http://{host}:{port}/health",
        f"  - http://{host}:{port}/health/live",
        f"  - http://{host}:{port}/health/ready",
        f"  - http://{host}:{port}/health/providers",
        "\nPress Ctrl+C to stop.",
    ]


def all_health_results_healthy(results: HealthResults) -> bool:
    """Return True when every provider result is healthy."""
    return bool(results) and all(
        result.get("status", "unknown") == "healthy" for result in results.values()
    )


def render_health_results_json(results: HealthResults) -> str:
    """Render health results as formatted JSON."""
    return json.dumps(results, indent=2)


def _health_status_icon(status: str) -> str:
    """Map provider health status to CLI icon."""
    if status == "healthy":
        return "[OK]"
    if status == "degraded":
        return "[WARN]"
    return "[FAIL]"


def build_health_result_lines(results: HealthResults) -> list[str]:
    """Build human-readable health check output lines."""
    lines: list[str] = []
    for provider, result in results.items():
        status = str(result.get("status", "unknown"))
        line = f"  {_health_status_icon(status)} {provider}: {status}"
        if "latency_ms" in result:
            line += f" ({result['latency_ms']}ms)"
        if "error" in result:
            line += f" - {result['error']}"
        lines.append(line)
    return lines
