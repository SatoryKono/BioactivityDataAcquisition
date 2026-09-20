# pyright: reportImportCycles=false
# Import cycle residual tracked in allowlist (product burn-down).
"""Summary assembly helpers for manifest diagnostics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.manifest.diagnostics.composite_projection import (
    build_composite_dossier_projection,
)
from bioetl.application.services.control_plane.manifest.diagnostics.summary_support import (
    apply_artifact_publication_closure_policy,
    assemble_identity_graph,
    build_produced_artifact_trace,
    build_runtime_views,
)
from bioetl.application.services.control_plane.manifest.diagnostics.summary_support import (
    build_exact_replay_anchors as _build_exact_replay_anchors,
)
from bioetl.application.services.control_plane.manifest.diagnostics.summary_support import (
    build_final_summary_updates as _build_final_summary_updates,
)
from bioetl.application.services.control_plane.manifest.diagnostics.summary_support import (
    build_identity_graph as _build_identity_graph,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.diagnostics.dq_details import (
        DQDetailsSummary,
    )

_build_runtime_views = build_runtime_views


@dataclass(frozen=True, slots=True)
class _FinalSummaryRequest:
    """Structured input for final manifest diagnostics summary assembly."""

    manifest: RunManifest
    base_summary: dict[str, object]
    ledger_entries: tuple[RunLedgerEntry, ...]
    family_counter: Counter[str]
    type_counter: Counter[str]
    artifact_refs: list[dict[str, object]]
    lineage_fragment_ids: set[str]
    dq_details: DQDetailsSummary
    missing_link_count: int
    correlation_anchor_gaps: dict[str, int]
    resume_diagnostics: dict[str, object] | None


@dataclass(frozen=True, slots=True)
class _RuntimeViewsRequest:
    """Structured inputs for persistence and operator-alert overlays."""

    manifest: RunManifest
    summary: dict[str, object]
    ledger_entries_present: bool
    artifact_refs: list[dict[str, object]]
    lineage_fragment_ids: set[str]
    missing_link_count: int
    latest_status: str | None
    dq_signal_present: bool
    cross_validation_signal_present: bool


def _build_final_summary(request: _FinalSummaryRequest) -> dict[str, object]:
    """Build final summary with all processed data."""
    exact_replay_anchors = _build_exact_replay_anchors(
        manifest=request.manifest,
        summary=request.base_summary,
        artifact_refs=request.artifact_refs,
        lineage_fragment_ids=request.lineage_fragment_ids,
    )
    produced_artifact_trace = build_produced_artifact_trace(
        manifest=request.manifest,
        ledger_entries_present=bool(request.ledger_entries),
        artifact_refs=request.artifact_refs,
    )
    identity_graph = _build_identity_graph(
        request,
        exact_replay_anchors=exact_replay_anchors,
        produced_artifact_trace=produced_artifact_trace,
    )
    latest_status = (
        request.ledger_entries[-1].status if request.ledger_entries else None
    )
    persistence_profile, alert_signals, next_steps = _build_runtime_views(
        _RuntimeViewsRequest(
            manifest=request.manifest,
            summary=request.base_summary,
            ledger_entries_present=bool(request.ledger_entries),
            artifact_refs=request.artifact_refs,
            lineage_fragment_ids=request.lineage_fragment_ids,
            missing_link_count=request.missing_link_count,
            latest_status=latest_status,
            dq_signal_present=request.dq_details["has_signal"],
            cross_validation_signal_present=request.dq_details[
                "has_cross_validation_signal"
            ],
        )
    )
    composite_dossier_projection = build_composite_dossier_projection(
        request,
        persistence_profile=persistence_profile,
    )
    summary = request.base_summary.copy()
    summary.update(
        _build_final_summary_updates(
            request,
            identity_graph=identity_graph,
            persistence_profile=persistence_profile,
            composite_dossier_projection=composite_dossier_projection,
            alert_signals=alert_signals,
            next_steps=next_steps,
            exact_replay_anchors=exact_replay_anchors,
            produced_artifact_trace=produced_artifact_trace,
        )
    )
    return apply_artifact_publication_closure_policy(summary)


def attach_base_summary_artifact_defaults(
    *,
    manifest: RunManifest,
    summary: dict[str, object],
) -> dict[str, object]:
    """Attach empty-ledger artifact defaults used by the base summary path."""
    summary["artifact_refs"] = []
    summary["lineage_fragment_ids"] = []
    summary["published_artifact_count"] = 0
    summary["exact_replay_anchors"] = _build_exact_replay_anchors(
        manifest=manifest,
        summary=summary,
        artifact_refs=[],
        lineage_fragment_ids=frozenset(),
    )
    produced_artifact_trace = build_produced_artifact_trace(
        manifest=manifest,
        ledger_entries_present=False,
        artifact_refs=[],
    )
    summary["produced_artifact_trace"] = produced_artifact_trace
    summary["artifact_publication_closure"] = produced_artifact_trace.get(
        "artifact_publication_closure"
    )
    summary["identity_graph_complete"] = None
    summary["identity_graph"] = assemble_identity_graph(manifest, summary)
    return summary
