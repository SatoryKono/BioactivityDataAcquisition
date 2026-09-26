"""Thin composition re-export of domain sink idempotency policy (#11226)."""

from __future__ import annotations

from bioetl.domain.control_plane.run_manifest_sink_policy import (
    validate_reproducible_sink_modes,
)

__all__ = ["validate_reproducible_sink_modes"]
