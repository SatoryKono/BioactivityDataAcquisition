"""Exact-run persisted assessment HTTP projection, independent of Prometheus."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from bioetl.application.observability.reason_aliases import display_reason
from bioetl.application.services.control_plane.manifest.diagnostics.selected_run_replay_readiness import (
    INSUFFICIENT,
    empty_replay_readiness,
    project_selected_run_replay_readiness,
)
from bioetl.composition.composite_catalog import (
    attach_contract_fields,
    project_assay_replay,
)
from bioetl.domain.ports import RunReportStorePort
from bioetl.domain.run_reports.selected_status import (
    provider_check_rows,
    provider_selector_options,
)
from bioetl.domain.run_reports.stage_diagnostics import project_stage_diagnostics
from bioetl.interfaces.http._forensic_request_budget import (
    ForensicEndpointUnavailable,
    run_bounded_forensic_operation,
)
from bioetl.interfaces.http._health_server_observability_protocols import (
    _HealthObservabilityRoutingHost,
)
from bioetl.interfaces.http._reconciliation_display import linked_reconciliation_display
from bioetl.interfaces.http._selected_run_a2_resolve import (
    CATALOG_UNAVAILABLE_REASON,
    NO_RUNS_REASON,
    NO_RUNS_STATUS,
    is_unresolved_run_id,
    list_a2_catalog,
    resolve_a2_latest_run_id,
)
from bioetl.interfaces.http._selected_run_artifact_probes import _artifact_probes
from bioetl.interfaces.http._selected_run_live import (
    active_run_diagnostics,
    scope_matches,
)
from bioetl.interfaces.http._selected_run_presentation import (
    _assessment_summary,
    _readiness_fields,
    presentation_rows,
)
from bioetl.application.services.evidence_location.resolver import EvidenceLocationResolver
from bioetl.interfaces.http._selected_run_report_assessment import (
    _IdentityMismatchError,
    _load_report_assessment,
    _manifest_snapshot,
    _RevisionMissingError,
    _saved_trust,
    _selected_pipeline,
)
from bioetl.interfaces.http._selected_run_unavailable import unavailable_status
from bioetl.interfaces.http.run_report_ops import _validated_artifact_paths

_NOT_EVALUATED = "NOT EVALUATED"
_QUERY_ERROR = "QUERY ERROR"
_CONTROL_PLANE = "Control Plane"

_NO_RUNS = NO_RUNS_STATUS


def _present_status(
    summary: dict[str, object],
    report: dict[str, object],
    domain_rows: list[dict[str, object]],
    readiness_fields: dict[str, object],
) -> dict[str, object]:
    """Format domain rows, Trust and presentation mirrors for one saved report."""
    issues = [
        f"{row['domain']}: {display_reason(str(row.get('reason', '')))}"
        for row in domain_rows
        if row.get("verdict") not in {"OK", "N/A"}
    ]
    if issues:
        summary["reason"] = "; ".join(issues)
    rows = [
        {
            **summary,
            **row,
            "run_verdict": summary["verdict"],
            "display_verdict": row["verdict"],
            "reason_display": display_reason(str(row.get("reason", ""))),
        }
        for row in domain_rows
    ]
    trust = _saved_trust(report, summary, rows)
    for row in rows:
        if row["domain"] == _CONTROL_PLANE:
            row["reason_display"] = trust["reasons_display"] or "No saved Trust reasons"
            row["display_verdict"] = trust["trust_status"]
    return attach_contract_fields(
        {
            **summary,
            "summary": [summary],
            "presentation_summary": [summary],
            "presentation_trust": [trust],
            "domains": rows,
            "presentation_domains": presentation_rows(rows),
            "provider_checks": provider_check_rows(report),
            "provider_options": provider_selector_options(report),
            "quality_evidence": {
                "pipeline": summary["pipeline"],
                "funnel": report.get("funnel"),
            },
            "rows": rows,
            "trust": [trust],
            **readiness_fields,
            **project_stage_diagnostics(report),
        }
    )


def _load_saved_assessment(
    path: Path, pipeline: str, run_id: str
) -> (
    tuple[dict[str, object], dict[str, object], dict[str, object], str, str]
    | dict[str, object]
):
    try:
        return _load_report_assessment(path, pipeline, run_id)
    except _IdentityMismatchError:
        return unavailable_status(pipeline, run_id, "ERROR", "identity_mismatch")
    except _RevisionMissingError:
        return unavailable_status(pipeline, run_id, "INCOMPLETE", "revision_missing")
    except (ValueError, TypeError, UnicodeError):
        return unavailable_status(pipeline, run_id, "ERROR", "evidence_corrupt")
    except OSError:
        return unavailable_status(
            pipeline, run_id, _QUERY_ERROR, "evidence_read_failed"
        )


def load_selected_run_status(
    *,
    pipeline: str,
    run_id: str,
    root: Path | None = None,
    manifest_port: object | None = None,
    store: RunReportStorePort | None = None,
    resolver: EvidenceLocationResolver | None = None,
) -> dict[str, object]:
    """Load and revalidate the exact report, revision and bound identity each time.

    Unresolved ``run_id`` sentinels are A2 empty-catalog gaps («НЕТ ЗАПУСКОВ»)
    when called without a prior auto-select. HTTP handling resolves latest first.
    """
    if is_unresolved_run_id(run_id):
        return unavailable_status(pipeline, "-", _NO_RUNS, NO_RUNS_REASON)
    try:
        selected_pipeline = _selected_pipeline(pipeline, run_id, root, store)
    except ValueError as exc:
        return unavailable_status(pipeline, run_id, "ERROR", str(exc))
    if selected_pipeline is None:
        return unavailable_status(pipeline, run_id, "UNKNOWN", "run_not_found")
    pipeline = selected_pipeline

    resolved_context = None
    if resolver is not None:
        try:
            resolved = resolver.resolve(kind="pipeline", owner=pipeline, run_id=run_id)
            resolved_context = resolved.context
        except BaseException:
            pass

    path = None
    if resolved_context is not None:
        report_path = getattr(resolved_context, "_path", lambda *a: None)(pipeline, run_id, "pipeline_run_report_json")
        if report_path is None:
            try:
                report_path, _ = _validated_artifact_paths(pipeline, run_id, "pipeline_run_report_json", resolved_context.data_root)
            except ValueError:
                pass
        if report_path is not None and report_path.is_file():
            path = report_path
    if path is None:
        path, _ = _validated_artifact_paths(
            pipeline, run_id, "pipeline_run_report_json", root
        )
    if not path.is_file():
        return unavailable_status(pipeline, run_id, "UNKNOWN", "run_not_found")
    loaded = _load_saved_assessment(path, pipeline, run_id)
    if isinstance(loaded, dict):
        return loaded
    report, identity, assessment, availability, revision = loaded
    summary = _assessment_summary(
        report,
        identity,
        assessment,
        availability,
        revision,
        pipeline,
        run_id,
        heartbeat_now=_NOT_EVALUATED,
    )
    probes, inventory_present = _artifact_probes(report, path.parent)
    if assessment.get("evidence_completeness") != "COMPLETE":
        probes.append(
            {
                "code": "report_evidence_completeness",
                "result": "unknown",
                "reason": "report_evidence_incomplete",
                "evidence_ref": "#/selected_run_snapshot/assessment",
            }
        )
    manifest, replay_probe = project_assay_replay(
        path.parent, run_id, report, _manifest_snapshot(manifest_port, run_id)
    )
    if replay_probe is not None:
        probes.append(replay_probe)
    projection = project_selected_run_replay_readiness(
        identity=identity,
        manifest=manifest,
        artifact_probes=probes,
        inventory_present=inventory_present,
        evidence_revision=revision,
        checked_at=str(identity.get("completed_at") or ""),
    )
    summary["replay_readiness_now"] = projection["verdict"]
    readiness_fields = _readiness_fields(projection)
    domain_rows = assessment["domains"]
    assert isinstance(domain_rows, list)  # Produced by the verified assessment.
    result = _present_status(summary, report, domain_rows, readiness_fields)
    result["reconciliation_display"] = linked_reconciliation_display(report, root)
    return result


def _merge_active_diagnostics(
    active: Mapping[str, object],
    *,
    pipeline: str,
    run_id: str,
) -> dict[str, object]:
    merged = unavailable_status(
        str(active.get("pipeline", pipeline)),
        run_id,
        str(active["verdict"]),
        str(active["reason"]),
    )
    merged.update(active)
    # Provider identity is a manifest fact even when the check/report is missing.
    provider = active.get("provider")
    if isinstance(provider, str) and provider not in {"", "unknown", "UNKNOWN", "—"}:
        for row in cast(list[dict[str, object]], merged["provider_checks"]):
            row["provider"] = provider
        merged["provider_options"] = [{"text": provider, "value": provider}]
    for row in cast(list[dict[str, object]], merged["domains"]):
        row.update(active)
        row["run_verdict"] = active["verdict"]
    for field in ("summary", "presentation_summary"):
        for row in cast(list[dict[str, object]], merged[field]):
            row.update(active)
    for field in ("trust", "presentation_trust"):
        for row in cast(list[dict[str, object]], merged[field]):
            row["processing_status"] = active.get("execution_state", "UNKNOWN")
    merged["presentation_domains"] = presentation_rows(
        cast(list[dict[str, object]], merged["domains"])
    )
    live = empty_replay_readiness(
        pipeline=str(merged.get("pipeline") or pipeline),
        run_id=run_id,
        verdict=INSUFFICIENT,
        reason="live_run_not_archived",
    )
    merged["replay_readiness_now"] = INSUFFICIENT
    merged.update(_readiness_fields(live))
    return merged


def _resolve_a2_run_id(
    host: _HealthObservabilityRoutingHost,
    *,
    pipeline: str,
    query: dict[str, str],
) -> str | dict[str, object]:
    """Return concrete run_id or an unavailable payload for A2 auto-select."""
    if host._run_manifest_port is None:
        return unavailable_status(
            pipeline, "-", _QUERY_ERROR, CATALOG_UNAVAILABLE_REASON
        )
    manifests, workflow_manifests = list_a2_catalog(
        host._run_manifest_port,
        getattr(host, "_workflow_manifest_port", None),
    )
    latest = resolve_a2_latest_run_id(
        manifests=manifests,
        ledger_port=host._run_ledger_port,
        workflow_manifests=workflow_manifests,
        pipeline=pipeline,
        query=query,
        report_store=getattr(host, "_run_report_store", None),
    )
    if latest is None:
        return unavailable_status(pipeline, "-", _NO_RUNS, NO_RUNS_REASON)
    return latest


def _load_selected_with_live_fallback(
    host: _HealthObservabilityRoutingHost,
    *,
    pipeline: str,
    run_id: str,
    query: dict[str, str],
    skip_scope_check: bool,
) -> dict[str, object]:
    result = load_selected_run_status(
        pipeline=pipeline,
        run_id=run_id,
        manifest_port=host._run_manifest_port,
        store=host._run_report_store,
        resolver=getattr(host, "_evidence_location_resolver", None),
    )
    if result.get("reason") == "run_not_found":
        # URL/explicit run_id stays bound; never substitute a different latest.
        active = active_run_diagnostics(host, pipeline, run_id)
        if active is not None:
            result = _merge_active_diagnostics(active, pipeline=pipeline, run_id=run_id)
    if skip_scope_check:
        return result
    state = result.get("execution_state")
    if state not in {None, "UNKNOWN"} and not scope_matches(result, query):
        return unavailable_status(
            pipeline, run_id, "ERROR", "selector_context_mismatch"
        )
    return result


async def handle_selected_run_status(
    host: _HealthObservabilityRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Bound blocking reads and preserve explicit query errors for Grafana.

    Mode A2: unresolved ``run_id`` auto-selects latest in scope; empty catalog
    returns «НЕТ ЗАПУСКОВ». An explicit URL ``run_id`` wins over auto-select.
    Missing manifest catalog is QUERY ERROR, not an empty catalog.

    §3.4: concurrent identical scopes share one physical load via the
    HealthServer-local selected-run-status cache (TTL 30s). Transport and
    capacity failures raise so the cache keeps the last good snapshot.
    """
    pipeline = host._read_required_param(query, "pipeline")
    requested_run_id = host._read_optional_param(query, "run_id") or "-"

    def load() -> dict[str, object]:
        run_id = requested_run_id
        a2_resolved = False
        if is_unresolved_run_id(run_id):
            resolved = _resolve_a2_run_id(host, pipeline=pipeline, query=query)
            if isinstance(resolved, dict):
                return resolved
            run_id = resolved
            a2_resolved = True
        # A2 catalog membership already enforced filters (incl. workflow aliases);
        # do not re-reject via report.workflow_id vs Grafana workflow alias.
        return _load_selected_with_live_fallback(
            host,
            pipeline=pipeline,
            run_id=run_id,
            query=query,
            skip_scope_check=a2_resolved,
        )

    async def cached_load() -> dict[str, object]:
        # Propagate ForensicEndpointUnavailable / IO failures so the cache does
        # not store QUERY ERROR frames as a fresh success payload.
        return await run_bounded_forensic_operation(
            limiter=host._forensic_endpoint_limiter,
            operation_factory=lambda: asyncio.to_thread(load),
            endpoint="selected-run-status",
        )

    try:
        payload = await host._selected_run_status_cache.read(query, cached_load)
    except ForensicEndpointUnavailable as exc:
        payload = unavailable_status(
            pipeline, requested_run_id, _QUERY_ERROR, exc.reason
        )
        if exc.request_id is not None:
            payload["request_id"] = exc.request_id
    except (KeyError, OSError, RuntimeError, ValueError):
        payload = unavailable_status(
            pipeline, requested_run_id, _QUERY_ERROR, "request_failed"
        )
    await host._send_payload_response(writer, 200, payload)
