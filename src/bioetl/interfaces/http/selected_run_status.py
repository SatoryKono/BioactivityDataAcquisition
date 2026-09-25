"""Exact-run persisted assessment HTTP projection, independent of Prometheus."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from bioetl.application.observability.reason_aliases import (
    display_reason,
    display_reasons_text,
)
from bioetl.application.services.run_reports.query import list_pipeline_reports
from bioetl.composition.observability_runtime import create_run_report_store
from bioetl.domain.run_reports.selected_status import (
    DOMAINS,
    RULES_VERSION,
    assess_report,
    evidence_digest,
    verify_snapshot,
)
from bioetl.interfaces.http import run_report_ops
from bioetl.interfaces.http._forensic_request_budget import (
    ForensicEndpointUnavailable,
    run_bounded_forensic_operation,
)
from bioetl.interfaces.http._health_server_observability_protocols import (
    _HealthObservabilityRoutingHost,
)
from bioetl.interfaces.http._selected_run_live import (
    active_run_diagnostics,
    pipeline_owners,
    scope_matches,
)
from bioetl.interfaces.http._selected_run_presentation import presentation_rows
from bioetl.interfaces.http.run_report_ops import _validated_artifact_paths

_NOT_EVALUATED = "NOT EVALUATED"
_QUERY_ERROR = "QUERY ERROR"
_CONTROL_PLANE = "Control Plane"
_REPORT_SCHEMAS = {"pipeline_run_report_v1", "pipeline_run_report_v2"}

_SELECT_RUN = "SELECT RUN"


class _RevisionMissingError(LookupError):
    """Selected-run snapshot revision file is absent after identity checks."""


class _IdentityMismatchError(LookupError):
    """Persisted report identity does not match the requested pipeline/run."""


def unavailable_status(
    pipeline: str, run_id: str, state: str, reason: str
) -> dict[str, object]:
    """Emit explicit state rows so unavailable evidence never becomes a green zero."""
    rows = [
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
        "replay_readiness_now": _NOT_EVALUATED,
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
        "presentation_domains": presentation_rows(rows, selection=state == _SELECT_RUN),
        "rows": rows,
        "trust": [trust],
    }


def _accounting_conflicts(
    reconciliation: object, verdict: object
) -> list[str]:
    if not isinstance(reconciliation, dict):
        return []
    conflicts: list[str] = []
    for stage in ("silver", "gold"):
        prior = "bronze" if stage == "silver" else "silver"
        key = f"{stage}_vs_{prior}_status"
        if reconciliation.get(key) == "FAILING":
            conflicts.append(
                f"Saved report accounting conflict: {key}=FAILING, "
                f"delta={reconciliation.get(f'{stage}_delta', 'UNKNOWN')}. "
                f"Saved Trust verdict: {verdict}; inspect report and ledger."
            )
    return conflicts


def _saved_trust(
    report: dict[str, object], summary: dict[str, object], rows: list[dict[str, object]]
) -> dict[str, object]:
    """Project Trust from the same frozen inputs as the six-domain summary."""
    control = next(row for row in rows if row["domain"] == _CONTROL_PLANE)
    reasons: object = report
    for key in (
        "observations",
        _CONTROL_PLANE,
        "facts",
        "checks",
        "trust",
        "reasons_text",
    ):
        reasons = reasons.get(key) if isinstance(reasons, dict) else None
    reasons_text = reasons if isinstance(reasons, str) else str(control["reason"])
    conflicts = _accounting_conflicts(report.get("reconciliation"), control["verdict"])
    if conflicts:
        reasons_text = "\n".join(filter(None, (reasons_text, *conflicts)))
    return {
        "processing_status": str(summary["execution_state"]).lower(),
        "trust_status": "ERROR" if conflicts else control["verdict"],
        "saved_trust_status": control["verdict"],
        "accounting_integrity": "CONFLICT" if conflicts else "NO REPORTED CONFLICT",
        "reasons_text": reasons_text,
        "reasons_display": display_reasons_text(reasons_text),
        "reasons_count": sum(bool(line.strip()) for line in reasons_text.splitlines()),
        "evidence_observed_at": summary["evaluation_at"],
        "pipeline": summary["pipeline"],
        "run_id": summary["run_id"],
        "rules_version": summary["rules_version"],
        "revision": summary["revision"],
        "replay_readiness_now": _NOT_EVALUATED,
    }


def _selected_pipeline(pipeline: str, run_id: str, root: Path | None) -> str | None:
    """Resolve an aggregate selector only from an unambiguous exact report path."""
    owners = pipeline_owners(pipeline)
    if owners is not None and len(owners) == 1:
        return next(iter(owners))
    if run_report_ops._safe_segment(run_id) != run_id:
        raise ValueError("invalid_run_id")
    base = run_report_ops._effective_root(root)
    entries = list_pipeline_reports(
        pipeline_name=None,
        limit=None,
        root=base,
        store=create_run_report_store(),
    )
    matches = [
        entry.owner
        for entry in entries
        if entry.run_id == run_id and (owners is None or entry.owner in owners)
    ]
    if len(matches) > 1:
        raise ValueError("run_id_ambiguous")
    return matches[0] if matches else None


def _legacy_assessment(report: dict[str, object]) -> tuple[dict[str, object], str, str]:
    assessment = assess_report(report)
    assessment["evidence_completeness"] = "INCOMPLETE"
    if assessment["verdict"] in {"OK", "N/A"}:
        assessment["verdict"] = "INCOMPLETE"
    return assessment, "legacy_no_snapshot", evidence_digest(report)


def _snapshot_assessment(
    report: dict[str, object], snapshot: dict[str, object], path: Path
) -> tuple[dict[str, object], str, str]:
    if not verify_snapshot(snapshot):
        raise ValueError("snapshot_corrupt_or_rules_unsupported")
    evidence = {
        key: value for key, value in report.items() if key != "selected_run_snapshot"
    }
    if snapshot.get("evidence") != evidence:
        raise ValueError("snapshot_evidence_mismatch")
    revision = str(snapshot["revision"])
    revision_path = path.parent / "status-revisions" / f"{revision}.json"
    if not revision_path.resolve().is_relative_to(path.parent.resolve()):
        raise ValueError("revision_outside_selected_run")
    if not revision_path.is_file():
        raise _RevisionMissingError("revision_missing")
    if json.loads(revision_path.read_text(encoding="utf-8")) != snapshot:
        raise ValueError("revision_corrupt")
    assessment = snapshot["assessment"]
    if not isinstance(assessment, Mapping):
        raise ValueError("assessment_invalid")
    return dict(assessment), "AVAILABLE", revision


def _load_report_assessment(
    path: Path, pipeline: str, run_id: str
) -> tuple[dict[str, object], dict[str, object], dict[str, object], str, str]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(report, dict)
        or report.get("schema_version") not in _REPORT_SCHEMAS
    ):
        raise ValueError("report_schema_invalid")
    identity = report.get("identity")
    if (
        not isinstance(identity, dict)
        or identity.get("run_id") != run_id
        or identity.get("pipeline_name") != pipeline
    ):
        raise _IdentityMismatchError("identity_mismatch")
    snapshot = report.get("selected_run_snapshot")
    if snapshot is None:
        assessment, availability, revision = _legacy_assessment(report)
    else:
        if not isinstance(snapshot, dict):
            raise ValueError("snapshot_corrupt_or_rules_unsupported")
        assessment, availability, revision = _snapshot_assessment(
            report, snapshot, path
        )
    return report, identity, assessment, availability, revision


def load_selected_run_status(
    *, pipeline: str, run_id: str, root: Path | None = None
) -> dict[str, object]:
    """Load and revalidate the exact report, revision and bound identity each time."""
    if run_id in {"", "-", "All", "$__all"}:
        return unavailable_status(pipeline, run_id, _SELECT_RUN, "selection_required")
    try:
        selected_pipeline = _selected_pipeline(pipeline, run_id, root)
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
    try:
        report, identity, assessment, availability, revision = _load_report_assessment(
            path, pipeline, run_id
        )
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
        "replay_readiness_now": _NOT_EVALUATED,
        "heartbeat_now": _NOT_EVALUATED,
        "reason": "Saved run evidence; CURRENT and chart coverage are separate",
    }
    domain_rows = assessment["domains"]
    assert isinstance(domain_rows, list)  # Produced by the verified assessment.
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
        "rows": rows,
        "trust": [trust],
    }


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
        result = load_selected_run_status(pipeline=pipeline, run_id=run_id)
        if result.get("reason") == "run_not_found":
            active = active_run_diagnostics(host, pipeline, run_id)
            if active is not None:
                result = _merge_active_diagnostics(active, pipeline=pipeline, run_id=run_id)
        state = result.get("execution_state")
        if state not in {None, "UNKNOWN"} and not scope_matches(result, query):
            return unavailable_status(pipeline, run_id, "ERROR", "selector_context_mismatch")
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
