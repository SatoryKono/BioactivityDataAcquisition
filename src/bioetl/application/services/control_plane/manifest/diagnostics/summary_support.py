"""Pure final-summary support helpers for manifest diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.services.control_plane.manifest.diagnostics.artifact_support import (
    apply_artifact_publication_closure_policy,
    build_produced_artifact_trace,
)
from bioetl.application.services.control_plane.manifest.diagnostics.persistence_alerts import (
    build_alert_signals,
    build_next_steps,
)
from bioetl.application.services.control_plane.manifest.diagnostics.persistence_profiles import (
    build_persistence_profile,
)
from bioetl.application.services.control_plane.manifest.diagnostics.summary_support_build_exact_replay_anchors import (
    build_exact_replay_anchors,
)
from bioetl.application.services.control_plane.manifest.identity_graph_assembly import (
    RunManifestIdentityGraphAssembler,
)
from bioetl.domain.control_plane.execution_context import (
    is_composite_execution_context as _is_composite_execution_context,
)

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.diagnostics.summary import (
        _FinalSummaryRequest,
        _RuntimeViewsRequest,
    )

assemble_identity_graph = RunManifestIdentityGraphAssembler.build


def _resolve_policy_value(values: set[str]) -> str | None:
    if not values:
        return None
    if len(values) == 1:
        return next(iter(values))
    return "mixed"


def build_identity_graph(
    request: _FinalSummaryRequest,
    *,
    exact_replay_anchors: dict[str, object],
    produced_artifact_trace: dict[str, object],
) -> dict[str, object]:
    """Assemble the operator-facing run identity graph via the canonical seam."""
    diagnostics_seed = {
        **request.base_summary,
        "exact_replay_anchors": exact_replay_anchors,
        "produced_artifact_trace": produced_artifact_trace,
        "artifact_refs": request.artifact_refs,
        "occurrence_only_diagnostics": sorted(
            request.dq_details["occurrence_only_diagnostic_scopes"]
        ),
        "resume_diagnostics": request.resume_diagnostics,
        "total_events": len(request.ledger_entries),
    }
    diagnostics_seed.pop("identity_graph", None)
    identity_graph = assemble_identity_graph(request.manifest, diagnostics_seed)
    identity_graph["published_artifacts"] = [
        dict(artifact_ref)
        for artifact_ref in request.artifact_refs
        if isinstance(artifact_ref, dict)
    ]
    return identity_graph


def build_alert_bundle(
    request: _RuntimeViewsRequest,
    *,
    persistence_profile: dict[str, object],
) -> tuple[dict[str, bool], list[str]]:
    """Return alert signals and operator next steps for final summary."""
    composite_execution_context = _is_composite_execution_context(request.manifest)
    composite_rich_replay_supported = bool(
        request.summary.get(
            "composite_resume_rich_replay_supported",
            not composite_execution_context,
        )
    )
    alert_signals = build_alert_signals(
        latest_status=request.latest_status,
        artifact_refs=request.artifact_refs,
        lineage_fragment_ids=request.lineage_fragment_ids,
        missing_link_count=request.missing_link_count,
        composite_resume_reconstructability_gap=(
            composite_execution_context and not composite_rich_replay_supported
        ),
        dq_signal_present=request.dq_signal_present,
        cross_validation_signal_present=request.cross_validation_signal_present,
        required_persistence_profile_missing_requirements=cast(
            list[str],
            persistence_profile.get("required_profile_missing_requirements", []),
        ),
        replay_ready_missing_requirements=cast(
            list[str],
            persistence_profile.get("replay_ready_missing_requirements", []),
        ),
        forensic_grade_missing_requirements=cast(
            list[str],
            persistence_profile.get("forensic_grade_missing_requirements", []),
        ),
    )
    return alert_signals, build_next_steps(alert_signals)


def build_runtime_views(
    request: _RuntimeViewsRequest,
) -> tuple[dict[str, object], dict[str, bool], list[str]]:
    """Return canonical persistence and operator overlays for one summary."""
    persistence_profile = build_persistence_profile(
        base_summary=request.summary,
        ledger_entries_present=request.ledger_entries_present,
        artifact_refs=request.artifact_refs,
        lineage_fragment_ids=request.lineage_fragment_ids,
        missing_link_count=request.missing_link_count,
    )
    alert_signals, next_steps = build_alert_bundle(
        request,
        persistence_profile=persistence_profile,
    )
    return persistence_profile, alert_signals, next_steps


def build_final_summary_updates(
    request: _FinalSummaryRequest,
    *,
    identity_graph: dict[str, object],
    persistence_profile: dict[str, object],
    composite_dossier_projection: dict[str, object],
    alert_signals: dict[str, bool],
    next_steps: list[str],
    exact_replay_anchors: dict[str, object],
    produced_artifact_trace: dict[str, object],
) -> dict[str, object]:
    """Return the summary update payload layered onto the base summary."""
    latest_entry = request.ledger_entries[-1]
    return {
        "total_events": len(request.ledger_entries),
        "latest_event_type": latest_entry.event_type,
        "latest_status": latest_entry.status,
        "event_family_counts": dict(sorted(request.family_counter.items())),
        "event_type_counts": dict(sorted(request.type_counter.items())),
        "artifact_refs": request.artifact_refs,
        "exact_replay_anchors": exact_replay_anchors,
        "produced_artifact_trace": produced_artifact_trace,
        "artifact_publication_closure": produced_artifact_trace.get(
            "artifact_publication_closure"
        ),
        "planned_artifact_count": len(request.manifest.planned_artifacts),
        "published_artifact_count": len(request.artifact_refs),
        "lineage_fragment_ids": sorted(request.lineage_fragment_ids),
        "missing_artifact_links": request.missing_link_count,
        "dq_rule_ids": sorted(request.dq_details["rule_ids"]),
        "dq_dispositions": sorted(request.dq_details["dispositions"]),
        "dq_report_paths": sorted(request.dq_details["report_paths"]),
        "dq_violation_kinds": sorted(request.dq_details["violation_kinds"]),
        "cross_validation_rule_ids": sorted(
            request.dq_details["cross_validation_rule_ids"]
        ),
        "cross_validation_config_paths": sorted(
            request.dq_details["cross_validation_config_paths"]
        ),
        "cross_validation_quarantine_policy": _resolve_policy_value(
            request.dq_details["cross_validation_quarantine_policies"]
        ),
        "cross_validation_quarantine_replay_contract": _resolve_policy_value(
            request.dq_details["cross_validation_replay_contracts"]
        ),
        "occurrence_only_diagnostics": sorted(
            request.dq_details["occurrence_only_diagnostic_scopes"]
        ),
        "resume_diagnostics": request.resume_diagnostics,
        "composite_dossier_projection": composite_dossier_projection,
        "cross_validation_signal_present": request.dq_details[
            "has_cross_validation_signal"
        ],
        "correlation_anchor_gaps": request.correlation_anchor_gaps,
        "identity_graph_complete": request.missing_link_count == 0
        and not any(request.correlation_anchor_gaps.values()),
        "identity_graph": identity_graph,
        "persistence_profile": persistence_profile,
        "alert_signals": alert_signals,
        "next_steps": next_steps,
    }


__all__ = [
    "apply_artifact_publication_closure_policy",
    "build_alert_bundle",
    "build_exact_replay_anchors",
    "build_final_summary_updates",
    "build_identity_graph",
    "build_produced_artifact_trace",
    "build_runtime_views",
]
