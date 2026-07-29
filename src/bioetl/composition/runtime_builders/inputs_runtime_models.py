"""Leaf runtime-input models shared by resolver helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResolvedVacuumSettings:
    """Resolved vacuum policy inputs for runtime configuration assembly."""

    enabled: bool
    retention_days: int


__all__ = ["ResolvedVacuumSettings"]
