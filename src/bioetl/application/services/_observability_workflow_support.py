"""Private support helpers for observability workflow dossiers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.application.services._observability_trace_support import (
    build_trace_ids,
    build_trace_urls,
    resolve_manifest_provider,
    resolve_manifest_run_type,
    resolve_primary_composite_run_id,
)
from bioetl.application.services._observability_trace_support import (
    trace_links_enabled as _trace_links_enabled,
)
from bioetl.application.services.audit_inspection_service import AuditInspectionResult
from bioetl.application.services.checkpoint_service import CheckpointInfo
from bioetl.application.services.control_plane.run_manifest_inspection_service import (
    RunManifestInspectionResult,
)

if TYPE_CHECKING:
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageRunExplanationResult,
    )

_CRITICAL_EVIDENCE_PROFILES = frozenset({"forensic_grade"})

__all__ = [
    "build_next_steps",
    "build_status_section",
    "build_traceability_section",
    "classify_evidence_status",
    "enrich_quarantine_summary",
    "resolve_checkpoint_for_run",
    "resolve_lineage_for_run",
    "resolve_pipeline_name",
    "resolve_run_manifest",
    "trace_links_enabled",
]


class _CheckpointLookupService(Protocol):
    async def get_checkpoint(self, pipeline_name: str) -> CheckpointInfo | None: ...


class _LineageExplainService(Protocol):
    def explain_run(self, run_id: str) -> LineageRunExplanationResult: ...


class _RunManifestShowService(Protocol):
    def show(self, identifier: str) -> RunManifestInspectionResult: ...


def trace_links_enabled(tracer: object | None) -> bool:
    return _trace_links_enabled(tracer)


def resolve_pipeline_name(
    run_manifest: RunManifestInspectionResult | None,
) -> str | None:
    if run_manifest is None:
        return None
    return run_manifest.manifest.pipeline_name


async def resolve_checkpoint_for_run(
    *,
    checkpoint_service: _CheckpointLookupService,
    run_id: str,
    pipeline_name: str | None,
) -> CheckpointInfo | None:
    if pipeline_name is None:
        return None
    checkpoint = await checkpoint_service.get_checkpoint(pipeline_name)
    if checkpoint is None:
        return None
    if checkpoint.run_id in {None, run_id}:
        return checkpoint
    return CheckpointInfo(
        pipeline_name=checkpoint.pipeline_name,
        run_id=checkpoint.run_id,
        metadata={**checkpoint.metadata, "status": "mismatched_run_context"},
    )


def resolve_lineage_for_run(
    lineage_service: _LineageExplainService | None,
    run_id: str,
) -> LineageRunExplanationResult | None:
    if lineage_service is None:
        return None
    try:
        return lineage_service.explain_run(run_id)
    except ValueError:
        return None


def resolve_run_manifest(
    run_manifest_service: _RunManifestShowService | None,
    identifier: str,
) -> RunManifestInspectionResult | None:
    if run_manifest_service is None:
        return None
    try:
        return run_manifest_service.show(identifier)
    except ValueError:
        return None


def resolve_bronze_record_count(
    run_manifest: RunManifestInspectionResult,
) -> int | None:
    bronze_records: int | None = None
    for entry in run_manifest.ledger_entries:
        metrics_snapshot = getattr(entry, "metrics_snapshot", None)
        if not isinstance(metrics_snapshot, dict):
            continue
        value = metrics_snapshot.get("records_bronze")
        if not isinstance(value, int) or value <= 0:
            continue
        bronze_records = value if bronze_records is None else max(bronze_records, value)
    return bronze_records


def enrich_quarantine_summary(
    *,
    stats: dict[str, object],
    run_id: str,
    run_manifest: RunManifestInspectionResult | None,
) -> dict[str, object]:
    summary = dict(stats)
    summary["run_scope"] = {"run_id": run_id}
    silver_stats = summary.get("silver_filter_rejects")
    if (
        run_manifest is not None
        and isinstance(silver_stats, dict)
        and isinstance(silver_stats.get("total_count"), int)
    ):
        bronze_records = resolve_bronze_record_count(run_manifest)
        if bronze_records is not None:
            silver_total = silver_stats["total_count"]
            silver_stats["bronze_records"] = bronze_records
            silver_stats["bronze_ratio"] = silver_total / bronze_records
            silver_stats["bronze_ratio_pct"] = (silver_total / bronze_records) * 100
    return summary


def build_traceability_section(
    *,
    run_id: str,
    run_manifest: RunManifestInspectionResult | None,
    lineage: LineageRunExplanationResult | None,
    audit: AuditInspectionResult,
    trace_links_enabled: bool,
) -> dict[str, object]:
    diagnostics = run_manifest.diagnostics if run_manifest is not None else {}
    identity_graph = run_manifest.identity_graph if run_manifest is not None else {}
    provider = resolve_manifest_provider(run_manifest)
    run_type = resolve_manifest_run_type(run_manifest)
    composite_run_id = resolve_primary_composite_run_id(diagnostics)
    trace_urls = (
        build_trace_urls(
            run_id=run_id,
            pipeline_name=resolve_pipeline_name(run_manifest),
            provider=provider,
            run_type=run_type,
            composite_run_id=composite_run_id,
            run_manifest=run_manifest,
            audit=audit,
        )
        if trace_links_enabled
        else []
    )
    trace_ids = build_trace_ids(
        run_id=run_id,
        diagnostics=diagnostics,
        trace_links_available=bool(trace_urls),
    )
    traceability = {
        "audit_entries_count": len(audit.entries),
        "identity_graph_complete": diagnostics.get("identity_graph_complete"),
        "correlation_anchor_gaps": diagnostics.get("correlation_anchor_gaps"),
        "lineage_fragment_ids": diagnostics.get("lineage_fragment_ids")
        or (list(lineage.fragment_ids) if lineage is not None else []),
        "artifact_refs": diagnostics.get("artifact_refs", []),
        "trace_ids": trace_ids,
        "trace_urls": trace_urls,
        "trace_links_available": bool(trace_urls),
        "persistence_profile": diagnostics.get("persistence_profile"),
        "replay_capability": identity_graph.get("replay_capability")
        or diagnostics.get("replay_capability"),
    }
    composite_projection = diagnostics.get("composite_dossier_projection")
    if composite_projection is not None:
        traceability["composite_projection"] = composite_projection
    return traceability


def classify_evidence_status(
    *,
    run_manifest: RunManifestInspectionResult | None,
    checkpoint: CheckpointInfo | None,
    lineage: LineageRunExplanationResult | None,
    quarantine_summary: dict[str, object] | None,
    traceability: dict[str, object],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    missing = ["run_manifest"] if run_manifest is None else []
    degraded = classify_checkpoint_status(checkpoint)
    if lineage is None:
        degraded.append("lineage")
    if quarantine_summary is None:
        degraded.append("quarantine_summary")
    degraded.extend(collect_traceability_degradation(traceability))
    if requires_critical_dossier_evidence(run_manifest) and (missing or degraded):
        degraded.append("critical_dossier_evidence_gap")
    return tuple(missing), tuple(degraded)


def requires_critical_dossier_evidence(
    run_manifest: RunManifestInspectionResult | None,
) -> bool:
    """Return whether this run requires forensic-grade dossier evidence."""
    if run_manifest is None:
        return False
    diagnostics = run_manifest.diagnostics
    if diagnostics.get("critical_pipeline") is True:
        return True
    return resolve_required_evidence_profile(diagnostics) in _CRITICAL_EVIDENCE_PROFILES


def resolve_required_evidence_profile(diagnostics: dict[str, object]) -> str | None:
    """Resolve the evidence profile required by runtime/control-plane policy."""
    persistence_profile = diagnostics.get("persistence_profile")
    if isinstance(persistence_profile, dict):
        required_profile = persistence_profile.get("required_profile")
        if isinstance(required_profile, str) and required_profile:
            return required_profile
    required_profile = diagnostics.get("required_persistence_profile")
    if isinstance(required_profile, str) and required_profile:
        return required_profile
    return None


def classify_checkpoint_status(checkpoint: CheckpointInfo | None) -> list[str]:
    if checkpoint is None:
        return ["checkpoint"]
    if checkpoint.metadata.get("status") == "mismatched_run_context":
        return ["checkpoint_mismatched_run"]
    return []


def collect_traceability_degradation(traceability: dict[str, object]) -> list[str]:
    degraded: list[str] = []
    persistence_profile = traceability.get("persistence_profile")
    if isinstance(persistence_profile, dict):
        degraded.extend(collect_persistence_profile_degradation(persistence_profile))
    if has_correlation_anchor_gaps(traceability):
        degraded.append("correlation_anchor_gaps")
    if has_composite_correlation_policy_gap(traceability):
        degraded.append("composite_correlation_policy_gap")
    if not traceability.get("trace_links_available", False):
        degraded.append("trace_links_unavailable")
    return degraded


def collect_persistence_profile_degradation(
    persistence_profile: dict[str, object],
) -> list[str]:
    degraded: list[str] = []
    attained = persistence_profile.get("attained_profile")
    if attained not in {None, "forensic_grade"}:
        degraded.append(f"persistence_profile:{attained}")
    for key in (
        "required_profile_missing_requirements",
        "replay_ready_missing_requirements",
        "forensic_grade_missing_requirements",
    ):
        value = persistence_profile.get(key)
        if isinstance(value, list) and value:
            degraded.append(key)
    return degraded


def has_correlation_anchor_gaps(traceability: dict[str, object]) -> bool:
    correlation_gaps = traceability.get("correlation_anchor_gaps")
    return isinstance(correlation_gaps, dict) and any(
        isinstance(value, int) and value > 0 for value in correlation_gaps.values()
    )


def has_composite_correlation_policy_gap(traceability: dict[str, object]) -> bool:
    composite_projection = traceability.get("composite_projection")
    if not isinstance(composite_projection, dict):
        return False
    if composite_projection.get("composite_run_id_consistent") is False:
        return True
    correlation_policy = composite_projection.get("correlation_policy")
    return isinstance(correlation_policy, dict) and correlation_policy.get(
        "status"
    ) not in {None, "satisfied"}


def build_next_steps(
    *,
    run_manifest: RunManifestInspectionResult | None,
    missing_evidence: tuple[str, ...],
    degraded_evidence: tuple[str, ...],
) -> tuple[str, ...]:
    steps = list(_manifest_next_steps(run_manifest))
    steps.extend(_missing_evidence_steps(missing_evidence))
    steps.extend(_degraded_evidence_steps(degraded_evidence))
    seen: dict[str, None] = {}
    return tuple(
        step for step in steps if not (step in seen or seen.setdefault(step, None))
    )


def _manifest_next_steps(
    run_manifest: RunManifestInspectionResult | None,
) -> tuple[str, ...]:
    if run_manifest is None:
        return ()
    diagnostics_steps = run_manifest.diagnostics.get("next_steps")
    if not isinstance(diagnostics_steps, list):
        return ()
    return tuple(str(step) for step in diagnostics_steps)


def _missing_evidence_steps(missing_evidence: tuple[str, ...]) -> tuple[str, ...]:
    if "run_manifest" not in missing_evidence:
        return ()
    return ("Persist and inspect run-manifest/ledger artifacts for this run.",)


def _degraded_evidence_steps(degraded_evidence: tuple[str, ...]) -> tuple[str, ...]:
    steps: list[str] = []
    if any(item.startswith("persistence_profile:") for item in degraded_evidence):
        steps.append(
            "Review required persistence profile before treating this run as "
            "forensic-grade."
        )
    if "critical_dossier_evidence_gap" in degraded_evidence:
        steps.append(
            "Resolve dossier evidence gaps before marking this critical run "
            "operationally successful."
        )
    if "trace_links_unavailable" in degraded_evidence:
        steps.append(
            "Use audit, manifest, and lineage sections as the current traceability "
            "fallback."
        )
    if "composite_correlation_policy_gap" in degraded_evidence:
        steps.append(
            "Repair composite_run_id correlation anchors before using the dossier "
            "as authoritative composite traceability evidence."
        )
    return tuple(steps)


def build_status_section(
    *,
    run_manifest: RunManifestInspectionResult | None,
    checkpoint: CheckpointInfo | None,
    lineage: LineageRunExplanationResult | None,
    quarantine_summary: dict[str, object] | None,
    missing_evidence: tuple[str, ...],
    degraded_evidence: tuple[str, ...],
) -> dict[str, object]:
    diagnostics = run_manifest.diagnostics if run_manifest is not None else {}
    persistence_profile = diagnostics.get("persistence_profile")
    attained_profile = (
        persistence_profile.get("attained_profile")
        if isinstance(persistence_profile, dict)
        else None
    )
    operational_success_criteria = build_operational_success_criteria(
        diagnostics=diagnostics,
        attained_profile=attained_profile,
        missing_evidence=missing_evidence,
        degraded_evidence=degraded_evidence,
    )
    return {
        "forensic_profile": attained_profile,
        "latest_status": diagnostics.get("latest_status"),
        "latest_event_type": diagnostics.get("latest_event_type"),
        "checkpoint_status": (
            "missing"
            if checkpoint is None
            else checkpoint.metadata.get("status", "present")
        ),
        "lineage_status": "present" if lineage is not None else "missing",
        "quarantine_status": (
            "present" if quarantine_summary is not None else "missing"
        ),
        "missing_evidence_count": len(missing_evidence),
        "degraded_evidence_count": len(degraded_evidence),
        "operational_success": operational_success_criteria["operational_success"],
        "operational_success_criteria": operational_success_criteria,
    }


def build_operational_success_criteria(
    *,
    diagnostics: dict[str, object],
    attained_profile: object,
    missing_evidence: tuple[str, ...],
    degraded_evidence: tuple[str, ...],
) -> dict[str, object]:
    """Build dossier-backed success criteria for operator decisions."""
    required_profile = resolve_required_evidence_profile(diagnostics)
    critical_pipeline = (
        diagnostics.get("critical_pipeline") is True
        or required_profile in _CRITICAL_EVIDENCE_PROFILES
    )
    persistence_profile = diagnostics.get("persistence_profile")
    required_profile_satisfied = True
    if isinstance(persistence_profile, dict) and isinstance(
        persistence_profile.get("required_profile_satisfied"), bool
    ):
        required_profile_satisfied = bool(
            persistence_profile["required_profile_satisfied"]
        )
    runtime_terminal_success = diagnostics.get("latest_status") == "success"
    dossier_evidence_satisfied = (
        required_profile_satisfied and not missing_evidence and not degraded_evidence
    )
    operational_success = runtime_terminal_success and (
        dossier_evidence_satisfied if critical_pipeline else True
    )
    return {
        "critical_pipeline": critical_pipeline,
        "runtime_terminal_success": runtime_terminal_success,
        "required_evidence_profile": required_profile,
        "attained_evidence_profile": attained_profile,
        "required_profile_satisfied": required_profile_satisfied,
        "dossier_evidence_satisfied": dossier_evidence_satisfied,
        "operational_success": operational_success,
    }
