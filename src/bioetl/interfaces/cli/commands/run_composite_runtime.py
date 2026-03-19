"""Compatibility shim for run-composite runtime module."""

from __future__ import annotations

from bioetl.interfaces.cli.commands.domains.composite.runtime import (
    build_runtime_config,
    echo_composite_startup,
    parse_enrich_only,
)

__all__ = [
    "build_runtime_config",
    "echo_composite_startup",
    "parse_enrich_only",
]
