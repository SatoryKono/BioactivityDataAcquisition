"""Private support helpers for observability workflow dossiers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from bioetl.application.services.audit_inspection_service import AuditInspectionResult
from bioetl.application.services.checkpoint_service import CheckpointInfo
from bioetl.application.services.control_plane.run_manifest_inspection_service import (
    RunManifestInspectionResult,
)

if TYPE_CHECKING:
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageRunExplanationResult,
    )

TRACE_DRILLDOWN_PATH = "/a/grafana-exploretraces-app/"
TRACE_DRILLDOWN_DEFAULT_FROM = "now-24h"
TRACE_DRILLDOWN_DEFAULT_TO = "now"
TRACE_WINDOW_PADDING = timedelta(minutes=5)


def resolve_pipeline_name(
    run_manifest: RunManifestInspectionResult | None,
) -> str | None:
    if run_manifest is None:
        return None
    return run_manifest.manifest.pipeline_name


async def resolve_checkpoint_for_run(
    *,
    checkpoint_service: object,
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
    lineage_service: object | None,
    run_id: str,
) -> LineageRunExplanationResult | None:
    if lineage_service is None:
        return None
    try:
        return lineage_service.explain_run(run_id)
    except ValueError:
        return None


def resolve_run_manifest(
    run_manifest_service: object | None,
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
    trace_urls = (
        build_trace_urls(
            run_id=run_id,
            pipeline_name=resolve_pipeline_name(run_manifest),
            provider=provider,
            run_type=run_type,
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
    return {
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


def trace_links_enabled(tracer: object | None) -> bool:
    if tracer is None:
        return False
    return getattr(tracer, "is_noop", False) is not True


def build_trace_ids(
    *,
    run_id: str,
    diagnostics: dict[str, object],
    trace_links_available: bool,
) -> list[str]:
    explicit_trace_ids = diagnostics.get("trace_ids")
    if isinstance(explicit_trace_ids, list):
        normalized = [
            value.strip()
            for value in explicit_trace_ids
            if isinstance(value, str) and value.strip()
        ]
        if normalized:
            return list(dict.fromkeys(normalized))
    if trace_links_available and run_id:
        return [run_id]
    return []


def resolve_manifest_provider(
    run_manifest: RunManifestInspectionResult | None,
) -> str | None:
    if run_manifest is None:
        return None
    provider = getattr(run_manifest.manifest, "provider", None)
    return str(provider) if provider not in {None, ""} else None


def resolve_manifest_run_type(
    run_manifest: RunManifestInspectionResult | None,
) -> str | None:
    if run_manifest is None:
        return None
    run_type = getattr(run_manifest.manifest, "run_type", None)
    if hasattr(run_type, "value"):
        run_type = run_type.value
    return str(run_type) if run_type not in {None, ""} else None


def build_trace_urls(
    *,
    run_id: str,
    pipeline_name: str | None,
    provider: str | None,
    run_type: str | None,
    run_manifest: RunManifestInspectionResult | None,
    audit: AuditInspectionResult,
) -> list[str]:
    query = build_traceql_query(
        run_id=run_id,
        pipeline_name=pipeline_name,
        provider=provider,
        run_type=run_type,
    )
    if query is None:
        return []
    from_value, to_value = build_trace_time_window(
        run_manifest=run_manifest,
        audit=audit,
    )
    params = urlencode(
        {
            "from": from_value,
            "to": to_value,
            "datasource": "tempo",
            "queryType": "traceqlSearch",
            "query": query,
        }
    )
    return [f"{TRACE_DRILLDOWN_PATH}?{params}"]


def build_traceql_query(
    *,
    run_id: str,
    pipeline_name: str | None,
    provider: str | None,
    run_type: str | None,
) -> str | None:
    if not run_id:
        return None
    filters = [f'span."bioetl.run_id" = "{run_id}"']
    if pipeline_name:
        filters.append(f'span."bioetl.pipeline" = "{pipeline_name}"')
    if run_type:
        filters.append(f'span."bioetl.run_type" = "{run_type}"')
    if provider:
        filters.append(f'span."bioetl.provider" = "{provider}"')
    return "{ " + " && ".join(filters) + " }"


def build_trace_time_window(
    *,
    run_manifest: RunManifestInspectionResult | None,
    audit: AuditInspectionResult,
) -> tuple[str, str]:
    timestamps: list[datetime] = []
    manifest_created_at = (
        getattr(run_manifest.manifest, "created_at", None)
        if run_manifest is not None
        else None
    )
    normalized_manifest_time = normalize_datetime(manifest_created_at)
    if normalized_manifest_time is not None:
        timestamps.append(normalized_manifest_time)
    for entry in audit.entries:
        normalized_entry_time = normalize_datetime(entry.timestamp)
        if normalized_entry_time is not None:
            timestamps.append(normalized_entry_time)
    if not timestamps:
        return (TRACE_DRILLDOWN_DEFAULT_FROM, TRACE_DRILLDOWN_DEFAULT_TO)
    start = min(timestamps) - TRACE_WINDOW_PADDING
    end = max(timestamps) + TRACE_WINDOW_PADDING
    return (str(int(start.timestamp() * 1000)), str(int(end.timestamp() * 1000)))


def normalize_datetime(value: object) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


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
    return tuple(missing), tuple(degraded)


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
    if "trace_links_unavailable" in degraded_evidence:
        steps.append(
            "Use audit, manifest, and lineage sections as the current traceability "
            "fallback."
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
    }
