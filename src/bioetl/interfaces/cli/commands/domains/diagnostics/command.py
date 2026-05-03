"""Internal wrapper for the public diagnostics command module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.diagnostics import (
    COMMANDS,
    diagnostics,
    get_metrics_operator_profile,
    get_observability_diagnostics_bundle,
    get_quarantine_runtime_service,
)

__all__ = [
    "COMMANDS",
    "diagnostics",
    "get_metrics_operator_profile",
    "get_observability_diagnostics_bundle",
    "get_quarantine_runtime_service",
]
