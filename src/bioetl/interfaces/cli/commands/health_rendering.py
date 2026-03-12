"""Pure rendering helpers for health CLI commands."""

from __future__ import annotations

import json

__all__ = [
    "all_health_results_healthy",
    "build_health_result_lines",
    "build_health_server_info_lines",
    "render_health_results_json",
]


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


def all_health_results_healthy(results: dict[str, dict[str, str]]) -> bool:
    """Return True when every provider result is healthy."""
    return all(result.get("status", "unknown") == "healthy" for result in results.values())


def render_health_results_json(results: dict[str, dict[str, str]]) -> str:
    """Render health results as formatted JSON."""
    return json.dumps(results, indent=2)


def _health_status_icon(status: str) -> str:
    """Map provider health status to CLI icon."""
    if status == "healthy":
        return "[OK]"
    if status == "degraded":
        return "[WARN]"
    return "[FAIL]"


def build_health_result_lines(results: dict[str, dict[str, str]]) -> list[str]:
    """Build human-readable health check output lines."""
    lines: list[str] = []
    for provider, result in results.items():
        status = result.get("status", "unknown")
        line = f"  {_health_status_icon(status)} {provider}: {status}"
        if "latency_ms" in result:
            line += f" ({result['latency_ms']}ms)"
        if "error" in result:
            line += f" - {result['error']}"
        lines.append(line)
    return lines
