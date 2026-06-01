"""Legacy import wrapper for effective-config context helpers."""

from __future__ import annotations

from bioetl.application.services.control_plane.effective_config.context import (
    build_effective_config_context,
)

__all__ = ["build_effective_config_context"]
