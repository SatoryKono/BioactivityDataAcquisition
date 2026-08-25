"""Compatibility re-export of composition health contracts."""

from __future__ import annotations

from bioetl.composition.contracts.health import (
    BronzeCleanupServiceProtocol,
    HealthServerDependenciesProtocol,
)

__all__ = [
    "BronzeCleanupServiceProtocol",
    "HealthServerDependenciesProtocol",
]
