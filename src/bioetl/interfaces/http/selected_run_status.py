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
    project_assay_replay,
)
from bioetl.domain.ports import RunReportStorePort
from bioetl.domain.run_reports.selected_status import (
    DOMAINS,
    RULES_VERSION,
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
from bioetl.interfaces.http._reconciliation_display import (
    linked_reconciliation_display,
    unavailable_reconciliation,
)
from bioetl.interfaces.http._selected_run_artifact_probes import _artifact_probes
from bioetl.interfaces.http._selected_run_live import (
    active_run_diagnostics,
    scope_matches,
)
from bioetl.interfaces.http._selected_run_presentation import (
    _readiness_fields,
    presentation_rows,
)
from bioetl.interfaces.http._selected_run_report_assessment import (
    _IdentityMismatchError,
    _load_report_assessment,
    _manifest_snapshot,
    _RevisionMissingError,
    _saved_trust,
    _selected_pipeline,
)
from bioetl.interfaces.http.run_report_ops import _validated_artifact_paths

_NOT_EVALUATED = "NOT EVALUATED"
_QUERY_ERROR = "QUERY ERROR"
_CONTROL_PLANE = "Control Plane"

_SELECT_RUN = "SELECT RUN"


def unavailable_status(
    pipeline: str, run_id: str, state: str, reason: str
) -> dict[str, object]:
    """Emit explicit state rows so unavailable evidence never becomes a green zero."""
    rows: list[dict[str, object]] = [
        {
            "domain": domain,
            "verdict": state,
            "display_verdict": state,
            "reason": reason,
            "reason_display": display_reason(reason),
            "run_id": run_id,
            "pipeline": pipeline,
            "action": "Select run or inspect evidence",
        }
        for domain in DOMAINS
    ]
    summary = {
        "pipeline": pipeline,
        "run_id": run_id,
        "verdict": state,
        "reason": reason,
        "evidence_availability": reason,
        "rules_version": RULES_VERSION,
        "execution_state": "UNKNOWN",
        "checks_verdict": "UNKNOWN",
        "evidence_completeness": "INCOMPLETE",
        "replay_readiness_now": _readiness_state(state),
        "heartbeat_now": _NOT_EVALUATED,
    }
    for row in rows:
        row.update({**summary, **row, "run_verdict": state})
    trust = {
        "processing_status": "UNKNOWN",
        "trust_status": state,
        "reasons_text": reason,
        "reasons_display": display_reason(reason),
        "reasons_count": None,
        "trust_reasons_action": "Not assessed",
        "evidence_observed_at": None,
    }
    return {
        **summary,
        "summary": [summary],
        "presentation_summary": [
            {
                **summary,
                "pipeline": "No run selected",
                "run_id": "—",
                "execution_state": _SELECT_RUN,
                "evidence_completeness": _SELECT_RUN,
            }
            if summary["verdict"] == _SELECT_RUN
            else summary
        ],
        "presentation_trust": [
            {
                **trust,
                "processing_status": _SELECT_RUN,
                "reasons_display": "Choose a run",
            }
            if summary["verdict"] == _SELECT_RUN
            else trust
        ],
        "domains": rows,
        "reconciliation_display": unavailable_reconciliation(reason),
        "presentation_domains": presentation_rows(rows, selection=state == _SELECT_RUN),
        "provider_checks": [
            {
                "provider": "—",
                "check_result": state,
                "evidence": reason,
                "observed_at": None,
            }
        ],
        "provider_options": [],
        "quality_evidence": {"pipeline": pipeline, "funnel": None},
        "rows": rows,
        "trust": [trust],
        **_readiness_fields(
            empty_replay_readiness(
                pipeline=pipeline,
                run_id=run_id,
                verdict=_readiness_state(state),
                reason=reason,
            )
        ),
        **project_stage_diagnostics(None, request_state=state, request_reason=reason),
    }


def _readiness_state(state: str) -> str:
    if state == _SELECT_RUN:
        return _SELECT_RUN
    if state == _QUERY_ERROR:
        return _QUERY_ERROR
    return INSUFFICIENT


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
    return {
        **summary,
        "summary": [summary],
        "presentation_summary": [
            {
                **summary,
                "pipeline": "No run selected",
                "run_id": "—",
                "execution_state": _SELECT_RUN,
                "evidence_completeness": _SELECT_RUN,
            }
            if summary["verdict"] == _SELECT_RUN
            else summary
        ],
        "presentation_trust": [
            {
                **trust,
                "processing_status": _SELECT_RUN,
                "reasons_display": "Choose a run",
            }
            if summary["verdict"] == _SELECT_RUN
            else trust
        ],
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


def _load_saved_assessment(
    path: Path, pipeline: str, run_id: str
) -> (
    tuple[
        dict[str, object],
        dict[str, object],
        dict[str, object],
        str,
        str,
    ]
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
) -> dict[str, object]:
    """Load and revalidate the exact report, revision and bound identity each time."""
    if run_id in {"", "-", "All", "$__all"}:
        return unavailable_status(pipeline, run_id, _SELECT_RUN, "selection_required")
    try:
        selected_pipeline = _selected_pipeline(pipeline, run_id, root, store)
    except ValueError as exc:
        return unavailable_status(pipeline, run_id, "ERROR", str(exc))
    if selected_pipeline is None:
        return unavailable_status(pipeline, run_id, "UNKNOWN", "run_not_found")
    pipeline = selected_pipeline
    path, _ = _validated_artifact_paths(
        pipeline, run_id, "pipeline_run_report_json", root
    )
    if not path.is_file():
        return unavailable_status(pipeline, run_id, "UNKNOWN", "run_not_found")
    loaded = _load_saved_assessment(path, pipeline, run_id)
    if isinstance(loaded, dict):
        return loaded
    report, identity, assessment, availability, revision = loaded
    summary = {
        **{key: value for key, value in assessment.items() if key != "domains"},
        "pipeline": pipeline,
        "run_id": run_id,
        "completed_at": identity.get("completed_at"),
        "run_type": identity.get("run_type"),
        "workflow_id": identity.get("workflow_id"),
        "started_at": identity.get("started_at"),
        "evaluation_at": report.get("assessment_at", identity.get("completed_at")),
        "revision": revision,
        "evidence_availability": availability,
        "heartbeat_now": _NOT_EVALUATED,
        "reason": "Saved run evidence; CURRENT and chart coverage are separate",
    }
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


async def handle_selected_run_status(
    host: _HealthObservabilityRoutingHost,
    writer: asyncio.StreamWriter,
    query: dict[str, str],
) -> None:
    """Bound blocking reads and preserve explicit query errors for Grafana."""
    pipeline = host._read_required_param(query, "pipeline")
    run_id = host._read_optional_param(query, "run_id") or "-"

    def load() -> dict[str, object]:
        result = load_selected_run_status(
            pipeline=pipeline,
            run_id=run_id,
            manifest_port=host._run_manifest_port,
            store=host._run_report_store,
        )
        if result.get("reason") == "run_not_found":
            active = active_run_diagnostics(host, pipeline, run_id)
            if active is not None:
                result = _merge_active_diagnostics(
                    active, pipeline=pipeline, run_id=run_id
                )
        state = result.get("execution_state")
        if state not in {None, "UNKNOWN"} and not scope_matches(result, query):
            return unavailable_status(
                pipeline, run_id, "ERROR", "selector_context_mismatch"
            )
        return result

    try:
        payload = await run_bounded_forensic_operation(
            limiter=host._forensic_endpoint_limiter,
            operation_factory=lambda: asyncio.to_thread(load),
            endpoint="selected-run-status",
        )
    except ForensicEndpointUnavailable as exc:
        payload = unavailable_status(pipeline, run_id, _QUERY_ERROR, exc.reason)
        if exc.request_id is not None:
            payload["request_id"] = exc.request_id
    except (OSError, RuntimeError, ValueError):
        payload = unavailable_status(pipeline, run_id, _QUERY_ERROR, "request_failed")
    await host._send_payload_response(writer, 200, payload)
