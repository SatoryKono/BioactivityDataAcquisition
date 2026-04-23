"""Facade for the canonical control-plane seam."""

from __future__ import annotations

from bioetl.application.services.control_plane.run_manifest_diagnostics import (
    build_diagnostics_summary,
)

__all__ = [
    "build_diagnostics_summary",
]
