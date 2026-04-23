"""Facade for the canonical control-plane seam."""

from __future__ import annotations

from bioetl.application.services.control_plane.effective_config_service import (
    EffectiveConfigService,
    create_effective_config_service,
)

__all__ = [
    "EffectiveConfigService",
    "create_effective_config_service",
]
