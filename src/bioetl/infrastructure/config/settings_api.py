"""Narrow public settings accessors for non-config owners."""

from __future__ import annotations

from bioetl.infrastructure.config._base import (
    ObservabilitySettings,
    Settings,
    get_settings,
)

__all__ = ["ObservabilitySettings", "Settings", "get_settings"]
