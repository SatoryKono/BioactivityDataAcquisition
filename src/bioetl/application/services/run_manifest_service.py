"""Compatibility facade for the canonical control-plane seam."""

from __future__ import annotations

from bioetl.application.services.control_plane.run_manifest_service import (
    RunManifestCreateSpec,
    RunManifestService,
)

__all__ = [
    "RunManifestCreateSpec",
    "RunManifestService",
]
