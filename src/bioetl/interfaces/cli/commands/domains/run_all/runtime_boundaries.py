"""Runtime boundary imports for the public run-all CLI seam."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
    ensure_metrics_server_started,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    build_observability_backend_required_probe_paths,
    ensure_observability_backend_started,
    should_disable_transient_health_server,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration import (
    DEFAULT_HEALTH_SERVER_PORT,
    echo_health_server_info,
    health_server_context,
)
from bioetl.interfaces.cli.commands.domains.run.support import (
    build_cli_registry,
    resolve_context_registry,
)
from bioetl.interfaces.cli.formatters import echo_error, echo_info

__all__ = [
    "DEFAULT_HEALTH_SERVER_PORT",
    "build_cli_registry",
    "build_observability_backend_required_probe_paths",
    "echo_error",
    "echo_health_server_info",
    "echo_info",
    "ensure_metrics_server_started",
    "ensure_observability_backend_started",
    "health_server_context",
    "resolve_context_registry",
    "should_disable_transient_health_server",
]
