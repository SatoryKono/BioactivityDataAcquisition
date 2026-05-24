"""Public seam for immutable input-snapshot resolution helpers."""

from __future__ import annotations

from bioetl.composition.runtime_builders import (
    _input_snapshot_resolution as _snapshot_resolution,
)

collect_manifest_input_snapshot_refs = (
    _snapshot_resolution.collect_manifest_input_snapshot_refs
)
resolve_cached_bronze_input_snapshot_refs = (
    _snapshot_resolution.resolve_cached_bronze_input_snapshot_refs
)
resolve_manifest_input_snapshot_refs = (
    _snapshot_resolution.resolve_manifest_input_snapshot_refs
)
resolve_pipeline_input_snapshot_refs = (
    _snapshot_resolution.resolve_pipeline_input_snapshot_refs
)

__all__ = [
    "collect_manifest_input_snapshot_refs",
    "resolve_cached_bronze_input_snapshot_refs",
    "resolve_manifest_input_snapshot_refs",
    "resolve_pipeline_input_snapshot_refs",
]
