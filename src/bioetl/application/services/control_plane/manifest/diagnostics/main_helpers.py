"""Helper functions for main diagnostics.

Extracted from manifest/diagnostics.py to meet file size limits.
"""

from __future__ import annotations

from typing import cast

from bioetl.application.services.control_plane.manifest.diagnostics.base import (
    _build_checkpoint_anchor_projection,
    _build_effective_config_diagnostics,
)
from bioetl.application.services.control_plane.manifest.diagnostics.main_helpers_build_unified_reproducibility_diagnostics_policy_payload import _build_unified_reproducibility_diagnostics_policy_payload




def _build_unified_reproducibility_diagnostics_semantic_identity(
    summary: dict[str, object],
) -> dict[str, object]:
    """Build semantic identity section of unified reproducibility diagnostics."""
    return {
        "execution_fingerprint": summary.get("execution_fingerprint"),
        "resolved_config_hash": summary.get("resolved_config_hash"),
        "effective_config_hash": summary.get("effective_config_hash"),
        "effective_config_artifact_id": summary.get("effective_config_artifact_id"),
        "input_snapshot_identity_fingerprint": summary.get(
            "input_snapshot_identity_fingerprint"
        ),
        "snapshot_status": summary.get("snapshot_status"),
        "input_snapshot_ids": summary.get("input_snapshot_ids", []),
    }


def _build_unified_reproducibility_diagnostics_occurrence_identity(
    summary: dict[str, object],
) -> dict[str, object]:
    """Build occurrence identity section of unified reproducibility diagnostics."""
    return {
        "run_id": summary.get("run_id"),
        "manifest_id": summary.get("manifest_id"),
        "manifest_created_at": summary.get("manifest_created_at"),
        "occurrence_only_diagnostics": summary.get(
            "occurrence_only_diagnostics",
            [],
        ),
    }


def _build_unified_reproducibility_diagnostics_checkpoint_anchors(
    summary: dict[str, object],
) -> dict[str, object]:
    """Build checkpoint anchors section of unified reproducibility diagnostics."""
    return {
        "resume_contract": summary.get("resume_contract"),
        "resume_diagnostics": summary.get("resume_diagnostics"),
        **_build_checkpoint_anchor_projection(summary),
    }


def _build_unified_reproducibility_diagnostics_lineage(
    summary: dict[str, object],
    produced_artifact_trace: dict[str, object],
) -> dict[str, object]:
    """Build lineage section of unified reproducibility diagnostics."""
    return {
        "lineage_closure_boundary": summary.get("lineage_closure_boundary"),
        "lineage_fragment_ids": summary.get("lineage_fragment_ids", []),
        "planned_artifact_count": summary.get("planned_artifact_count"),
        "published_artifact_count": summary.get("published_artifact_count"),
        "artifact_publication_closure": summary.get("artifact_publication_closure"),
        "produced_artifact_trace_complete": produced_artifact_trace.get("complete"),
    }


def _build_unified_reproducibility_diagnostics(
    summary: dict[str, object],
) -> dict[str, object]:
    """Return a single operator-facing reproducibility diagnostics surface."""
    persistence_profile = cast(
        "dict[str, object]", summary.get("persistence_profile", {})
    )
    produced_artifact_trace = cast(
        "dict[str, object]",
        summary.get("produced_artifact_trace", {}),
    )
    policy_payload = _build_unified_reproducibility_diagnostics_policy_payload(
        summary=summary,
        persistence_profile=persistence_profile,
    )
    return {
        "policy": policy_payload,
        "semantic_identity": _build_unified_reproducibility_diagnostics_semantic_identity(
            summary
        ),
        "effective_config": _build_effective_config_diagnostics(summary),
        "occurrence_identity": _build_unified_reproducibility_diagnostics_occurrence_identity(
            summary
        ),
        "checkpoint_anchors": _build_unified_reproducibility_diagnostics_checkpoint_anchors(
            summary
        ),
        "lineage": _build_unified_reproducibility_diagnostics_lineage(
            summary, produced_artifact_trace
        ),
    }


__all__ = [
    "_build_unified_reproducibility_diagnostics",
]
