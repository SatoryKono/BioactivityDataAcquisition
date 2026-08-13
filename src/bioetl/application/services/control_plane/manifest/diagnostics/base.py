"""Base run-manifest diagnostics helper aggregation seam."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.diagnostics.summary_support import (
    build_produced_artifact_trace as _build_produced_artifact_trace,
)
from bioetl.application.services.control_plane.manifest.diagnostics.base_effective_config_diagnostics import (
    _build_effective_config_diagnostics,
)
from bioetl.application.services.control_plane.manifest.diagnostics.base_payload_sections import (
    _build_base_summary_core_payload,
)
from bioetl.application.services.control_plane.manifest.diagnostics.base_replay_context import (
    _BaseSummaryReplayContext,
    _resolve_base_summary_replay_context,
)
from bioetl.application.services.control_plane.manifest.diagnostics.checkpoint_projection import (
    build_checkpoint_anchor_projection as _build_checkpoint_anchor_projection,
)
from bioetl.application.services.control_plane.manifest.diagnostics.checkpoint_projection import (
    build_current_checkpoint_anchor_payload as _build_current_checkpoint_anchor_payload,
)
from bioetl.application.services.control_plane.manifest.diagnostics.checkpoint_projection import (
    build_resume_anchor_comparison as _build_resume_anchor_comparison,
)
from bioetl.application.services.control_plane.manifest.diagnostics.checkpoint_projection import (
    resolve_resume_identity_maps as _resolve_resume_identity_maps,
)
from bioetl.application.services.control_plane.manifest.diagnostics.summary_support import (
    build_exact_replay_anchors as _build_exact_replay_anchors,
)
from bioetl.domain.control_plane import RunManifest


def _build_base_summary_payload(
    manifest: RunManifest,
    replay_context: _BaseSummaryReplayContext,
) -> dict[str, object]:
    """Build the base diagnostics payload and attach artifact defaults."""
    code_provenance = manifest.code_provenance
    summary = _build_base_summary_core_payload(
        manifest=manifest,
        replay_context=replay_context,
    )
    if code_provenance.dependency_lock_hash is not None:
        summary["dependency_lock_hash"] = code_provenance.dependency_lock_hash
    return _attach_base_summary_artifact_defaults(
        manifest=manifest,
        summary=summary,
    )


def _attach_base_summary_artifact_defaults(
    *,
    manifest: RunManifest,
    summary: dict[str, object],
) -> dict[str, object]:
    summary["artifact_refs"] = []
    summary["lineage_fragment_ids"] = []
    summary["published_artifact_count"] = 0
    summary["exact_replay_anchors"] = _build_exact_replay_anchors(
        manifest=manifest,
        summary=summary,
        artifact_refs=[],
        lineage_fragment_ids=frozenset(),
    )
    produced_artifact_trace = _build_produced_artifact_trace(
        manifest=manifest,
        ledger_entries_present=False,
        artifact_refs=[],
    )
    summary["produced_artifact_trace"] = produced_artifact_trace
    summary["artifact_publication_closure"] = produced_artifact_trace.get(
        "artifact_publication_closure"
    )
    summary["identity_graph_complete"] = None
    return summary


__all__ = [
    "_BaseSummaryReplayContext",
    "_build_base_summary_payload",
    "_build_checkpoint_anchor_projection",
    "_build_current_checkpoint_anchor_payload",
    "_build_effective_config_diagnostics",
    "_build_resume_anchor_comparison",
    "_resolve_base_summary_replay_context",
    "_resolve_resume_identity_maps",
]
