"""Support helpers for metrics-server integration helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.interfaces.cli.commands._compat import alias_module

if TYPE_CHECKING:
    from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
        ensure_metrics_server_started as ensure_metrics_server_started,
    )
    from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
        metrics_server_context as metrics_server_context,
    )

alias_module(
    __name__,
    "bioetl.interfaces.cli.commands.domains.health.metrics_server_integration",
)
