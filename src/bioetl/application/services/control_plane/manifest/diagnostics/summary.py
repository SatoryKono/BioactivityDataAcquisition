"""Summary assembly helpers for manifest diagnostics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import cast

from bioetl.application.services.control_plane.manifest.diagnostics.artifact_support import (
    apply_artifact_publication_closure_policy,
    build_produced_artifact_trace,
    sorted_text_items,
)
from bioetl.application.services.control_plane.manifest.diagnostics.composite_projection import (
    build_composite_dossier_projection,
)
from bioetl.application.services.control_plane.manifest.diagnostics.dq_details import (
    DQDetailsSummary,
)
from bioetl.application.services.control_plane.manifest.diagnostics.ledger_processing import (
    _resolve_policy_value,
)
from bioetl.application.services.control_plane.manifest.diagnostics.persistence import (
    build_alert_signals,
    build_next_steps,
    build_persistence_profile,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_parentage import (
    _is_composite_execution_context,
)
from bioetl.application.services.control_plane.manifest.identity_graph_assembly import (
    RunManifestIdentityGraphAssembler,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest


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


def _build_exact_replay_anchors(
    *,
    manifest: RunManifest,
    summary: dict[str, object],
    artifact_refs: list[dict[str, object]],
    lineage_fragment_ids: set[str] | frozenset[str],
) -> dict[str, object]:
    """Return semantic replay anchors separately from occurrence diagnostics."""
    published_artifact_ids = sorted_text_items(
        [
            artifact_ref.get("dataset_ref") or artifact_ref.get("artifact_id")
            for artifact_ref in artifact_refs
        ]
    )
    published_artifact_paths = sorted_text_items(
        [artifact_ref.get("artifact_path") for artifact_ref in artifact_refs]
    )
    anchors: dict[str, object] = {
        "semantic_identity_anchor": "execution_fingerprint",
        "execution_fingerprint": manifest.execution_fingerprint,
        "pipeline_name": manifest.pipeline_name,
        "run_type": manifest.run_type.value,
        "pipeline_version": summary.get("pipeline_version"),
        "git_commit": summary.get("git_commit"),
        "dependency_lock_state": summary.get("dependency_lock_state"),
        "effective_config_hash": summary.get("effective_config_hash"),
        "dq_contract_compatibility_hash": summary.get("dq_contract_compatibility_hash"),
        "contract_ref": summary.get("contract_ref"),
        "contract_version": summary.get("contract_version"),
        "normalization_profile_ref": summary.get("normalization_profile_ref"),
        "normalization_profile_version": summary.get("normalization_profile_version"),
        "normalization_profile_hash": summary.get("normalization_profile_hash"),
        "effective_config_artifact_id": summary.get("effective_config_artifact_id"),
        "input_snapshot_identity_fingerprint": summary.get(
            "input_snapshot_identity_fingerprint"
        ),
        "input_snapshot_ids": sorted_text_items(summary.get("input_snapshot_ids", [])),
        "input_snapshot_content_hashes": sorted_text_items(
            summary.get("input_snapshot_content_hashes", [])
        ),
        "published_artifact_ids": published_artifact_ids,
        "published_artifact_paths": published_artifact_paths,
        "lineage_fragment_ids": sorted(lineage_fragment_ids),
    }
    if summary.get("dependency_lock_hash") is not None:
        anchors["dependency_lock_hash"] = summary.get("dependency_lock_hash")
    return anchors


def _build_identity_graph(
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
    return RunManifestIdentityGraphAssembler.build(
        request.manifest,
        diagnostics_seed,
    )


def _build_alert_bundle(
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


def _build_runtime_views(
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
    alert_signals, next_steps = _build_alert_bundle(
        request,
        persistence_profile=persistence_profile,
    )
    return persistence_profile, alert_signals, next_steps


def _build_final_summary_updates(
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
        "identity_graph_complete": (
            request.missing_link_count == 0
            and not any(request.correlation_anchor_gaps.values())
        ),
        "identity_graph": identity_graph,
        "persistence_profile": persistence_profile,
        "alert_signals": alert_signals,
        "next_steps": next_steps,
    }


def _build_final_summary(
    request: _FinalSummaryRequest,
) -> dict[str, object]:
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
    persistence_profile, alert_signals, next_steps = _build_runtime_views(
        _RuntimeViewsRequest(
            manifest=request.manifest,
            summary=request.base_summary,
            ledger_entries_present=bool(request.ledger_entries),
            artifact_refs=request.artifact_refs,
            lineage_fragment_ids=request.lineage_fragment_ids,
            missing_link_count=request.missing_link_count,
            latest_status=request.ledger_entries[-1].status,
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
