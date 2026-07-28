"""Health server integration for CLI commands.

Public facade that re-exports lifecycle, observability, deps, and option helpers
so existing CLI and test import paths remain stable.
"""

from __future__ import annotations

from bioetl.interfaces.cli.commands.domains.health.failure_handling import (
    handle_health_failure as _handle_health_failure,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration_deps import (
    build_health_server,
    build_health_server_pycache_prefix,
    close_health_server_resources,
    get_health_server_dependencies,
    get_health_server_quarantine_service,
    get_quarantine_runtime_service,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration_lifecycle import (
    DEFAULT_HEALTH_SERVER_PORT,
    health_server_context,
    run_long_lived_health_server_command,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration_observability import (
    _start_health_observability,
    get_metrics_server_starter,
    get_runtime_settings,
    start_metrics_server,
)
from bioetl.interfaces.cli.commands.domains.health.server_integration_options import (
    COMMANDS,
    add_health_server_options,
    echo_health_server_info,
)

__all__ = [
    "COMMANDS",
    "DEFAULT_HEALTH_SERVER_PORT",
    "_handle_health_failure",
    "_start_health_observability",
    "add_health_server_options",
    "build_health_server",
    "build_health_server_pycache_prefix",
    "close_health_server_resources",
    "echo_health_server_info",
    "get_health_server_dependencies",
    "get_health_server_quarantine_service",
    "get_metrics_server_starter",
    "get_quarantine_runtime_service",
    "get_runtime_settings",
    "health_server_context",
    "run_long_lived_health_server_command",
    "start_metrics_server",
]
