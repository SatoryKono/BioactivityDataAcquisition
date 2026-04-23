"""Facade for the canonical control-plane seam."""

from __future__ import annotations

from bioetl.application.services.control_plane.run_manifest_service import (
    RunManifestCreateSpec,
    RunManifestService,
)

# Compatibility alias for refactored naming
RunManifestCreateRequest = RunManifestCreateSpec

__all__ = [
    "RunManifestCreateRequest",
    "RunManifestCreateSpec",
    "RunManifestService",
]
