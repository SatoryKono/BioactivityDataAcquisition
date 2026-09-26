"""Exact-run persisted assessment HTTP projection, independent of Prometheus."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast
from uuid import UUID

from bioetl.application.observability.reason_aliases import (
    display_reason,
    display_reasons_text,
)
from bioetl.application.services.control_plane.manifest.diagnostics.selected_run_replay_readiness import (
    INSUFFICIENT,
    empty_replay_readiness,
    project_selected_run_replay_readiness,
)
from bioetl.application.services.run_reports.query import list_pipeline_reports
from bioetl.composition.observability_runtime import create_run_report_store
from bioetl.domain.run_reports.selected_status import (
    DOMAINS,
    RULES_VERSION,
    assess_report,
    evidence_digest,
    provider_check_rows,
    provider_selector_options,
    verify_snapshot,
)
from bioetl.domain.run_reports.stage_diagnostics import project_stage_diagnostics
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
_SELF_REPORT_KINDS = frozenset(
    {
        "pipeline_run_report_json",
        "pipeline_run_report_md",
        "workflow_run_report_json",
        "workflow_run_report_md",
    }
)
_SELF_REPORT_FILENAMES = {
    "pipeline_run_report_json": "pipeline-run-report.json",
    "pipeline_run_report_md": "pipeline-run-report.md",
    "workflow_run_report_json": "workflow-run-report.json",
    "workflow_run_report_md": "workflow-run-report.md",
}


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
        "trust_reasons_action": None,
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
        "provider_checks": [
            {
                "provider": "—",
                "check_result": state,
                "evidence": reason,
                "observed_at": None,
            }
        ],
        "provider_options": [],
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
        **project_stage_diagnostics(
            None, request_state=state, request_reason=reason
        ),
    }


def _readiness_state(state: str) -> str:
    if state == _SELECT_RUN:
        return _SELECT_RUN
    if state == _QUERY_ERROR:
        return _QUERY_ERROR
    return INSUFFICIENT


_UNKNOWN_CHECK_LABELS = {
    "manifest_not_recorded": "manifest for this run was not recorded",
}


def _readiness_fields(projection: Mapping[str, object]) -> dict[str, object]:
    blockers = projection.get("blockers")
    unknown = projection.get("unknown_checks")
    blocker_text = (
        ", ".join(blockers) if isinstance(blockers, list) and blockers else "—"
    )
    unknown_text = (
        ", ".join(_UNKNOWN_CHECK_LABELS.get(str(code), str(code)) for code in unknown)
        if isinstance(unknown, list) and unknown
        else "—"
    )
    row = {
        key: value
        for key, value in projection.items()
        if key not in {"checks", "blockers", "unknown_checks"}
    }
    row["blockers"] = blocker_text
    row["unknown_checks"] = unknown_text
    checks = projection.get("checks")
    return {
        "replay_readiness": [row],
        "replay_checks": checks if isinstance(checks, list) else [],
    }


def _resolve_artifact_path(
    root: Path, relative: str, kind: str
) -> tuple[Path | None, str]:
    """Locate an artifact without joining a repo-relative ref onto the run directory."""
    filename = _SELF_REPORT_FILENAMES.get(kind)
    if filename is not None:
        canonical = (root / filename).resolve()
        if canonical.is_file() and canonical.is_relative_to(root):
            return canonical, ""
    raw = Path(relative)
    if raw.is_absolute():
        candidate = raw.resolve()
        if not candidate.is_relative_to(root):
            return None, "artifact_path_escape"
        return candidate, ""
    if len(raw.parts) == 1:
        return (root / raw.name).resolve(), ""
    if kind in _SELF_REPORT_KINDS:
        return None, "artifact_missing"
    candidate = (root / raw).resolve()
    if not candidate.is_relative_to(root):
        return None, "artifact_path_escape"
    return candidate, ""


def _artifact_probes(
    report: Mapping[str, object], run_root: Path
) -> tuple[list[dict[str, str]], bool]:
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return [], False
    root = run_root.resolve()
    probes: list[dict[str, str]] = []
    for index, item in enumerate(artifacts):
        ref = f"#/artifacts/{index}"
        code = f"artifact_{index}"
        if not isinstance(item, dict):
            probes.append(
                {
                    "code": code,
                    "result": "fail",
                    "reason": "artifact_record_invalid",
                    "evidence_ref": ref,
                }
            )
            continue
        name = item.get("name") or item.get("id") or item.get("kind") or code
        code = str(name)
        relative = item.get("path") or item.get("relative_path") or item.get("ref")
        digest = item.get("sha256") or item.get("digest") or item.get("content_hash")
        if not isinstance(relative, str) or not relative.strip():
            probes.append(
                {
                    "code": code,
                    "result": "fail",
                    "reason": "hash_without_object"
                    if digest
                    else "artifact_path_missing",
                    "evidence_ref": ref,
                }
            )
            continue
        kind = str(item.get("kind") or "")
        candidate, resolve_error = _resolve_artifact_path(root, relative, kind or code)
        if resolve_error or candidate is None or not candidate.is_file():
            probes.append(
                {
                    "code": code,
                    "result": "fail",
                    "reason": resolve_error or "artifact_missing",
                    "evidence_ref": ref,
                }
            )
            continue
        if not isinstance(digest, str) or not digest.strip():
            if code in _SELF_REPORT_KINDS or kind in _SELF_REPORT_KINDS:
                probes.append(
                    {
                        "code": code,
                        "result": "pass",
                        "reason": "object_available",
                        "evidence_ref": ref,
                    }
                )
                continue
            probes.append(
                {
                    "code": code,
                    "result": "unknown",
                    "reason": "digest_not_recorded",
                    "evidence_ref": ref,
                }
            )
            continue
        actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if actual != digest.strip().lower():
            probes.append(
                {
                    "code": code,
                    "result": "fail",
                    "reason": "digest_mismatch",
                    "evidence_ref": ref,
                }
            )
            continue
        probes.append(
            {
                "code": code,
                "result": "pass",
                "reason": "digest_matches",
                "evidence_ref": ref,
            }
        )
    return probes, True


def _accounting_conflicts(reconciliation: object, verdict: object) -> list[str]:
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
    reasons_count = sum(bool(line.strip()) for line in reasons_text.splitlines())
    return {
        "processing_status": str(summary["execution_state"]).lower(),
        "trust_status": "ERROR" if conflicts else control["verdict"],
        "saved_trust_status": control["verdict"],
        "accounting_integrity": "CONFLICT" if conflicts else "NO REPORTED CONFLICT",
        "reasons_text": reasons_text,
        "reasons_display": display_reasons_text(reasons_text),
        "reasons_count": reasons_count,
        "trust_reasons_action": "View trust reasons" if reasons_count > 0 else None,
        "evidence_observed_at": summary["evaluation_at"],
        "pipeline": summary["pipeline"],
        "run_id": summary["run_id"],
        "rules_version": summary["rules_version"],
        "revision": summary["revision"],
        "replay_readiness_now": summary.get("replay_readiness_now", INSUFFICIENT),
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


def _manifest_snapshot(port: object, run_id: str) -> dict[str, object] | None:
    """Read manifest fields for this run. A missing port is not report identity."""
    if port is None:
        return None
    try:
        selected_id = UUID(run_id)
    except ValueError:
        return None
    getter = getattr(port, "get_by_run_id", None)
    if getter is None:
        return None
    manifest = getter(selected_id)
    if manifest is None:
        return None
    provenance = getattr(manifest, "code_provenance", None)
    fingerprints: list[str] = []
    for source in getattr(manifest, "source_refs", ()) or ():
        for snapshot in getattr(source, "input_snapshots", ()) or ():
            content_hash = getattr(snapshot, "content_hash", None)
            if isinstance(content_hash, str) and content_hash.strip():
                fingerprints.append(content_hash.strip())
    capability = getattr(manifest, "replay_capability", None)
    capability_value = getattr(capability, "value", capability)
    return {
        "effective_config_hash": getattr(provenance, "effective_config_hash", None),
        "dependency_lock_hash": getattr(provenance, "dependency_lock_hash", None),
        "input_snapshot_fingerprint": ",".join(fingerprints) if fingerprints else None,
        "replay_capability": capability_value,
        "replay_of_run_id": getattr(manifest, "replay_of_run_id", None),
        "replay_of_manifest_id": getattr(manifest, "replay_of_manifest_id", None),
    }


def load_selected_run_status(
    *,
    pipeline: str,
    run_id: str,
    root: Path | None = None,
    manifest_port: object | None = None,
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
        "heartbeat_now": _NOT_EVALUATED,
        "reason": "Saved run evidence; CURRENT and chart coverage are separate",
    }
    probes, inventory_present = _artifact_probes(report, path.parent)
    projection = project_selected_run_replay_readiness(
        identity=identity,
        manifest=_manifest_snapshot(manifest_port, run_id),
        artifact_probes=probes,
        inventory_present=inventory_present,
        evidence_revision=revision,
        checked_at=str(identity.get("completed_at") or ""),
    )
    summary["replay_readiness_now"] = projection["verdict"]
    readiness_fields = _readiness_fields(projection)
    domain_rows = assessment["domains"]
    assert isinstance(domain_rows, list)  # Produced by the verified assessment.
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
        "rows": rows,
        "trust": [trust],
        **readiness_fields,
        **project_stage_diagnostics(report),
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
