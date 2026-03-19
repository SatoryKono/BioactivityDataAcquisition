"""Thin wrapper re-exporting canonical CLI metrics-server helpers."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.domains.health.metrics_server_integration import (
    ensure_metrics_server_started,
    metrics_server_context,
)

__all__ = [
    "ensure_metrics_server_started",
    "metrics_server_context",
]
