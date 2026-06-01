"""Legacy import wrapper for manifest-owned validation helpers."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.validation import (
    validate_run_manifest_request,
)

__all__ = ["validate_run_manifest_request"]
