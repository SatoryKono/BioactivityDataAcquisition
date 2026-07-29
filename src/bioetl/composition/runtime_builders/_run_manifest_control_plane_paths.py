"""Writable data-root and control-plane path helpers for run manifests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._run_manifest_data_roots import (
    _resolve_data_root,
)

__all__ = ["_resolve_data_root", "control_plane_root"]

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings


def control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return _resolve_data_root(settings) / "output" / "control" / leaf
