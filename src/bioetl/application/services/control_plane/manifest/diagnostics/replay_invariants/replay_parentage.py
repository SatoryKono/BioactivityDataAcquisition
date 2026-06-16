"""Replay parentage and execution-context invariants for diagnostics."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics.nested_mapping import (
    lookup_mapping_path,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.execution_context import (
    is_composite_execution_context as _is_composite_execution_context,
)


def _is_full_scan_idempotent_rebuild(manifest: RunManifest) -> bool:
    if manifest.launch_context.get("full_scan_idempotent_rebuild", False):
        return True
    candidates = (
        manifest.runtime_config.get("loading_strategy"),
        lookup_mapping_path(manifest.runtime_config, "pipeline", "loading_strategy"),
        manifest.resolved_config.get("loading_strategy"),
        lookup_mapping_path(manifest.resolved_config, "pipeline", "loading_strategy"),
    )
    return any(
        str(candidate or "").strip().lower() == "full_scan_only"
        for candidate in candidates
    )


def _build_replay_parentage(manifest: RunManifest) -> dict[str, object]:
    replay_of_run_id = manifest.replay_of_run_id
    replay_of_manifest_id = manifest.replay_of_manifest_id
    return {
        "is_exact_replay": (
            replay_of_run_id is not None or replay_of_manifest_id is not None
        ),
        "replay_of_run_id": replay_of_run_id,
        "replay_of_manifest_id": replay_of_manifest_id,
    }


__all__ = [
    "_build_replay_parentage",
    "_is_composite_execution_context",
    "_is_full_scan_idempotent_rebuild",
]
