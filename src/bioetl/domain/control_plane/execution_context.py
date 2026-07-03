"""Execution-context helpers for control-plane replay policy."""

from __future__ import annotations

from bioetl.domain.control_plane.run_manifest import RunManifest


def is_composite_execution_context(manifest: RunManifest) -> bool:
    """Return whether a run manifest represents a composite execution."""
    return manifest.launch_context.get("execution_context") == "composite"


__all__ = ["is_composite_execution_context"]
