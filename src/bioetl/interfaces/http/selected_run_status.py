"""Exact-run persisted assessment HTTP projection, independent of Prometheus."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from bioetl.domain.run_reports.selected_status import (
    DOMAINS,
    RULES_VERSION,
    assess_report,
    evidence_digest,
    verify_snapshot,
)
from bioetl.interfaces.http._forensic_request_budget import (
    ForensicEndpointUnavailable,
    run_bounded_forensic_operation,
)
from bioetl.interfaces.http._health_server_observability_protocols import (
    _HealthObservabilityRoutingHost,
)
from bioetl.interfaces.http._selected_run_live import (
    active_run_diagnostics,
    scope_matches,
)
from bioetl.interfaces.http.run_report_ops import _validated_artifact_paths


def unavailable_status(
    pipeline: str, run_id: str, state: str, reason: str
) -> dict[str, object]:
    """Emit explicit state rows so unavailable evidence never becomes a green zero."""
    rows = [
        {
            "domain": domain,
            "verdict": state,
            "reason": reason,
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
    }
    return {**summary, "summary": [summary], "domains": rows, "rows": rows}


def load_selected_run_status(
    *, pipeline: str, run_id: str, root: Path | None = None
) -> dict[str, object]:
    """Load and revalidate the exact report, revision and bound identity each time."""
    if run_id in {"", "-", "All", "$__all"}:
        return unavailable_status(pipeline, run_id, "SELECT RUN", "selection_required")
    path, _ = _validated_artifact_paths(
        pipeline, run_id, "pipeline_run_report_json", root
    )
    if not path.is_file():
        return unavailable_status(pipeline, run_id, "UNKNOWN", "run_not_found")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(report, dict)
            or report.get("schema_version") != "pipeline_run_report_v1"
        ):
            raise ValueError("report_schema_invalid")
        identity = report.get("identity")
        if (
            not isinstance(identity, dict)
            or identity.get("run_id") != run_id
            or identity.get("pipeline_name") != pipeline
        ):
            return unavailable_status(pipeline, run_id, "ERROR", "identity_mismatch")
        snapshot = report.get("selected_run_snapshot")
        if snapshot is None:
            assessment = assess_report(report)
            availability, revision = "legacy_no_snapshot", evidence_digest(report)
            # Legacy reports lack the complete observation contract. Do not backfill.
            assessment["evidence_completeness"] = "INCOMPLETE"
            if assessment["verdict"] in {"OK", "N/A"}:
                assessment["verdict"] = "INCOMPLETE"
        else:
            if not isinstance(snapshot, dict) or not verify_snapshot(snapshot):
                raise ValueError("snapshot_corrupt_or_rules_unsupported")
            evidence = {
                key: value
                for key, value in report.items()
                if key != "selected_run_snapshot"
            }
            if snapshot.get("evidence") != evidence:
                raise ValueError("snapshot_evidence_mismatch")
            revision = str(snapshot["revision"])
            revision_path = path.parent / "status-revisions" / f"{revision}.json"
            if not revision_path.resolve().is_relative_to(path.parent.resolve()):
                raise ValueError("revision_outside_selected_run")
            if not revision_path.is_file():
                return unavailable_status(
                    pipeline, run_id, "INCOMPLETE", "revision_missing"
                )
            if json.loads(revision_path.read_text(encoding="utf-8")) != snapshot:
                raise ValueError("revision_corrupt")
            assessment = dict(snapshot["assessment"])
            availability = "AVAILABLE"
    except (ValueError, TypeError, UnicodeError):
        return unavailable_status(pipeline, run_id, "ERROR", "evidence_corrupt")
    except OSError:
        return unavailable_status(
            pipeline, run_id, "QUERY ERROR", "evidence_read_failed"
        )
    summary = {
        **{key: value for key, value in assessment.items() if key != "domains"},
        "pipeline": pipeline,
        "run_id": run_id,
        "completed_at": identity.get("completed_at"),
        "run_type": identity.get("run_type"),
        "workflow_id": identity.get("workflow_id"),
        "started_at": identity.get("started_at"),
        "evaluation_at": identity.get("completed_at"),
        "revision": revision,
        "evidence_availability": availability,
        "replay_readiness_now": "NOT EVALUATED",
        "heartbeat_now": "NOT EVALUATED",
        "reason": "Saved run evidence; CURRENT and chart coverage are separate",
    }
    domain_rows = assessment["domains"]
    assert isinstance(domain_rows, list)  # Produced by the verified assessment.
    rows = [
        {**row, "pipeline": pipeline, "run_id": run_id, "revision": revision}
        for row in domain_rows
    ]
    return {**summary, "summary": [summary], "domains": rows, "rows": rows}


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
                result = unavailable_status(
                    pipeline, run_id, str(active["verdict"]), str(active["reason"])
                )
                result.update(active)
                result["summary"] = [
                    {
                        key: value
                        for key, value in result.items()
                        if key not in {"summary", "domains", "rows"}
                    }
                ]
        if result.get("execution_state") and not scope_matches(result, query):
            return unavailable_status(
                pipeline, run_id, "ERROR", "selector_context_mismatch"
            )
        return result

    try:
        payload = await run_bounded_forensic_operation(
            limiter=host._forensic_endpoint_limiter,
            operation_factory=lambda: asyncio.to_thread(load),
        )
    except ForensicEndpointUnavailable as exc:
        payload = unavailable_status(pipeline, run_id, "QUERY ERROR", exc.reason)
    except (OSError, RuntimeError, ValueError):
        payload = unavailable_status(pipeline, run_id, "QUERY ERROR", "request_failed")
    await host._send_payload_response(writer, 200, payload)
