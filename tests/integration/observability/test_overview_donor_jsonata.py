"""Exercise the complete shared donor, including missing and offset dates."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from scripts.ops.observability.grafana.apply_phase25_srs_prr_budget import _OV_DONOR

pytestmark = pytest.mark.integration


def donor_payload(start, end):
    summary = {
        "started_at": start,
        "completed_at": end,
        "execution_state": "UNFINISHED" if end is None else "SUCCESS",
        "verdict": "INCOMPLETE" if end is None else "OK",
    }
    return {
        "run_id": "example",
        "pipeline": "example",
        "run_type": "incremental",
        "started_at": start,
        "execution_state": summary["execution_state"],
        "verdict": summary["verdict"],
        "summary": [summary],
        "presentation_summary": [summary],
        "presentation_domains": [{"domain": "Runtime", "verdict": summary["verdict"]}],
        "presentation_trust": [{"trust_status": "UNKNOWN"}],
        "provider_checks": [{"provider": "example", "evidence": "PRESENT"}],
        "stage_diagnostics": [],
        "reconciliation_display": [],
        "contract_exclusions_rate": None,
    }


def evaluate_donor(payload, expression=_OV_DONOR, *, offset_date_only=False):
    node = shutil.which("node")
    module = os.environ.get("JSONATA_MODULE")
    if not node or not module or not Path(module).exists():
        pytest.skip("Set JSONATA_MODULE to exercise the real JSONata engine")
    checked_clock = datetime(2026, 11, 11, 10, tzinfo=UTC)
    # Reproduce the deployed Infinity backend's offset parsing quirk separately
    # from standard JSONata; a JS-only run missed the live 18.5h-versus-7.8h bug.
    script = "const fs=require('fs'); const q=JSON.parse(fs.readFileSync(0,'utf8')); const expr=require(q.module)(q.expr); expr.registerFunction('now',()=>q.now); expr.registerFunction('millis',()=>q.millis); if(q.offset_date_only) expr.registerFunction('toMillis',t=>Date.parse(/[+-]\\d\\d:?\\d\\d$/.test(t)?t.slice(0,10):t)); expr.evaluate(q.payload).then(x=>process.stdout.write(JSON.stringify(x))).catch(e=>{console.error(e.message);process.exit(1)});"
    result = subprocess.run(
        [node, "-e", script],
        input=json.dumps(
            {
                "module": module,
                "expr": expression.replace("${run_id:percentencode}", "-"),
                "payload": payload,
                "now": checked_clock.isoformat(),
                "millis": checked_clock.timestamp() * 1000,
                "offset_date_only": offset_date_only,
            }
        ),
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("cache_state", ["fresh", "stale", "unavailable"])
def test_context_separates_cache_freshness_from_saved_assessment_and_run_result(
    cache_state,
):
    payload = donor_payload(None, None)
    payload["summary"][0]["evaluation_at"] = "2026-11-11T08:00:00+00:00"
    payload["status_cache"] = {"state": cache_state, "fresh_seconds": 30}
    rows = evaluate_donor(payload)
    context = next(r for r in rows if r["_bioetl_frame"] == "selection_context")
    assert (
        "Cache "
        + {"fresh": "FRESH", "stale": "STALE", "unavailable": "UNKNOWN"}[cache_state]
        in context["evidence_freshness"]
    )
    assert "2026-11-11 08:00 +00:00" in context["evidence_freshness"]
    assert len(context["evidence_freshness"]) <= 90
    assert context["execution_state"] == "UNFINISHED"


@pytest.mark.parametrize("profile", ["dashboards", "dashboards-adaptive"])
@pytest.mark.parametrize(
    ("uid", "panel_id"), [("bioetl-overview-v2", 99), ("bioetl-dq-v2", 9400)]
)
def test_context_columns_match_contract_and_evaluated_donor(profile, uid, panel_id):
    payload = donor_payload(None, None)
    payload["summary"][0]["evaluation_at"] = "2026-11-11T08:00:00Z"
    dashboard = json.loads(Path(f"grafana/{profile}/{uid}.json").read_text())
    panels = {panel["id"]: panel for panel in dashboard["panels"]}
    panel = source = panels[panel_id]
    visited = set()
    while source.get("datasource", {}).get("uid") == "-- Dashboard --":
        assert source["id"] not in visited, "Dashboard donor cycle"
        visited.add(source["id"])
        assert len(source["targets"]) == 1
        handoff = source["targets"][0]
        assert handoff["withTransforms"] is False, "Context must consume raw evidence"
        source = panels[handoff["panelId"]]
    assert source["datasource"]["uid"] == "bioetl-ops-http"
    target = source["targets"][0]
    assert target["parser"] == "backend"
    context = next(
        row
        for row in evaluate_donor(payload, target["root_selector"])
        if row["_bioetl_frame"] == "selection_context"
    )
    assert context["context"]
    assert datetime.fromisoformat(context["context_checked_at"]) == datetime(
        2026, 11, 11, 10, tzinfo=UTC
    )
    assert context["saved_assessment_at"] == "2026-11-11T08:00:00Z"
    assert context["assessment_age_seconds"] == 7200
    transforms = panel["transformations"]
    fields = next(
        t["options"]["include"]["names"]
        for t in transforms
        if t["id"] == "filterFieldsByName"
    )
    assert set(fields) <= context.keys(), (
        "Visible context columns must exist in the executed HTTP donor"
    )
    rename = next(
        t["options"]["renameByName"] for t in transforms if t["id"] == "organize"
    )
    contract = yaml.safe_load(
        Path(
            "docs/03-guides/dashboards/contracts/panel-content-contract.yaml"
        ).read_text(encoding="utf-8")
    )
    required = contract["dashboards"][uid]["panels"][str(panel_id)]["required_columns"]
    assert required == [rename.get(field, field) for field in fields]


@pytest.mark.parametrize(
    ("saved", "seconds"),
    [
        (None, None),
        ("2026-11-11T08:00:00Z", 7200),
        ("2026-11-11T11:00:00+03:00", 7200),
        ("2026-11-11T11:00:00Z", None),
    ],
)
@pytest.mark.parametrize("offset_date_only", [False, True])
def test_saved_assessment_age_uses_its_clock_not_reader_cache(
    saved, seconds, offset_date_only
):
    payload = donor_payload(None, None)
    payload["summary"][0]["evaluation_at"] = saved
    payload["status_cache"] = {"state": "fresh", "fresh_seconds": 30}
    rows = evaluate_donor(payload, offset_date_only=offset_date_only)
    context = next(row for row in rows if row["_bioetl_frame"] == "selection_context")
    assert context.get("saved_assessment_at") == saved
    assert context["assessment_age_seconds"] == seconds


def test_cached_bronze_note_does_not_invent_a_probe_time_from_completion():
    payload = donor_payload("2026-11-11T07:00:00Z", "2026-11-11T08:00:00Z")
    payload["presentation_domains"] = [
        {"domain": "Provider", "reason": "cached_bronze_no_remote_probe"}
    ]
    row = next(
        row for row in evaluate_donor(payload) if row["_bioetl_frame"] == "provider"
    )
    assert (
        row["provider_check_note"]
        == "Cached Bronze; API not called. Probe time: N/A (not performed)."
    )
    assert "08:00" not in row["provider_check_note"]


@pytest.mark.parametrize("profile", ["dashboards", "dashboards-adaptive"])
def test_replay_evidence_collapses_unselected_anchors_without_inventing_a_pass(profile):
    path = Path("grafana") / profile / "bioetl-control-plane-v1.json"
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    target = next(p for p in dashboard["panels"] if p["id"] == 9408)["targets"][0]
    assert target["parser"] == "backend"
    expression = target["root_selector"]
    anchors = [
        {"name": "present", "priority": 0, "present": True},
        {"name": "later", "priority": 2, "present": False},
        {"name": "zeta", "priority": 1, "present": False},
        {"name": "alpha", "priority": 1, "present": False},
    ]
    rows = evaluate_donor(
        {"summary": {"overall_status": "SELECT RUN"}, "rows": anchors * 44}, expression
    )
    assert len(rows) == 1
    assert rows[0]["status"] == "SELECT RUN" and rows[0]["present"] is False
    selected = evaluate_donor(
        {"summary": {"overall_status": "OK"}, "rows": anchors}, expression
    )
    assert [row["name"] for row in selected] == ["alpha", "zeta", "later", "present"]
    error = evaluate_donor({"status": "scope_resolve_timeout"}, expression)
    assert len(error) == 1 and error[0]["status"] == "QUERY ERROR"


@pytest.mark.parametrize("state", ["SELECT RUN", "NO RUNS", "QUERY ERROR"])
@pytest.mark.parametrize("profile", ["dashboards", "dashboards-adaptive"])
def test_full_replay_donor_preserves_gap_and_error_frames_with_null_reason_count(
    state, profile
):
    from bioetl.interfaces.http.selected_run_status import unavailable_status

    path = Path("grafana") / profile / "bioetl-control-plane-v1.json"
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    target = next(p for p in dashboard["panels"] if p["id"] == 9418)["targets"][0]
    assert target["parser"] == "backend"
    payload = unavailable_status(".*", "-", state, "exact_run_required")
    rows = evaluate_donor(payload, target["root_selector"])
    readiness = next(row for row in rows if row["_bioetl_frame"] == "replay_readiness")
    trust = next(row for row in rows if row["_bioetl_frame"] == "trust")
    assert readiness["verdict"] == state
    assert trust["trust_status"] == state
    assert trust["trust_action_note"] == "Not assessed"
    checks = [row for row in rows if row["_bioetl_frame"] == "replay_checks"]
    assert len(checks) == 1
    assert checks[0]["code"] == "selection"
    assert checks[0]["result"] == "n/a"
    assert checks[0]["reason"] == "exact_run_required"


@pytest.mark.parametrize("profile", ["dashboards", "dashboards-adaptive"])
@pytest.mark.parametrize("generator", ["phase25", "exact_replay"])
def test_replay_generators_preserve_backend_donor_and_dashboard_children(
    profile, generator
):
    from scripts.ops.observability.grafana._replay_readiness_design import (
        stamp_exact_replay_queries,
    )
    from scripts.ops.observability.grafana.apply_phase25_srs_prr_budget import (
        apply_control_plane,
    )

    path = Path("grafana") / profile / "bioetl-control-plane-v1.json"
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    shipped = deepcopy(
        next(p for p in dashboard["panels"] if p["id"] == 9418)["targets"]
    )
    apply_control_plane(dashboard)
    if generator == "exact_replay":
        stamp_exact_replay_queries(dashboard)
    panels = {panel["id"]: panel for panel in dashboard["panels"]}
    target = panels[9418]["targets"][0]
    assert target["parser"] == "backend"
    assert "uql" not in target
    assert target["root_selector"] == shipped[0]["root_selector"]
    assert target["url"] == shipped[0]["url"]
    for pid, frame in ((9422, "replay_readiness"), (9423, "replay_checks")):
        child = panels[pid]
        assert child["datasource"]["uid"] == "-- Dashboard --"
        assert child["targets"][0]["panelId"] == 9418
        assert frame in json.dumps(child["transformations"])


@pytest.mark.parametrize(
    ("start", "end", "duration"),
    [
        (None, None, "Not recorded"),
        ("2026-11-11T10:00:00+00:00", None, "Not recorded"),
        (None, "2026-11-11T10:00:00Z", "Not recorded"),
        ("2026-11-11T10:00:00Z", "2026-11-11T10:03:10Z", "3 min 10 s"),
        ("2026-11-11T10:00:00+00:00", "2026-11-11T10:03:10+00:00", "3 min 10 s"),
        ("2026-11-11T13:00:00.123+03:00", "2026-11-11T10:03:10.623Z", "3 min 11 s"),
        ("2026-11-11T05:00:00-0500", "2026-11-11T11:00:00+0100", "0 s"),
        (
            "2026-11-11T10:03:00Z",
            "2026-11-11T10:00:00Z",
            "Not recorded",
        ),
    ],
)
def test_full_overview_donor_keeps_context_with_missing_or_offset_dates(
    start, end, duration
):
    rows = evaluate_donor(donor_payload(start, end))
    identity = {
        r["parameter"]: r["value"] for r in rows if r["_bioetl_frame"] == "identity"
    }
    assert identity["Run duration"] == duration
    context = next(r for r in rows if r["_bioetl_frame"] == "selection_context")
    assert context["context"] == "AUTO · latest run in scope"
    assert context["execution_state"] == ("UNFINISHED" if end is None else "SUCCESS")


def test_full_donor_provider_age_uses_clock_and_offset():
    completed = (
        datetime(2026, 11, 11, 10, tzinfo=UTC) - timedelta(seconds=90)
    ).isoformat()
    rows = evaluate_donor(donor_payload(None, completed))
    provider = next(r for r in rows if r["_bioetl_frame"] == "provider")
    assert provider["observed_display"] == "1 min ago"


def test_full_donor_empty_catalog_keeps_explained_context():
    payload = donor_payload(None, None)
    payload.update(
        run_id="-",
        reason="no_runs_in_scope",
        summary=[],
        presentation_summary=[],
        presentation_domains=[],
        provider_checks=[],
    )
    rows = evaluate_donor(payload)
    context = next(r for r in rows if r["_bioetl_frame"] == "selection_context")
    assert context["context"] == "NO RUN · empty scope"


@pytest.mark.parametrize(
    "limits,expected",
    [
        (None, "Limits unavailable; check config"),
        (0.05, "Accounting incomplete; inspect stages"),
    ],
)
def test_unknown_exclusions_explain_the_gap_instead_of_inventing_zero(limits, expected):
    payload = donor_payload(None, None)
    payload.update(
        contract_exclusions_status="UNKNOWN",
        contract_exclusions_soft_limit=limits,
        contract_exclusions_hard_limit=limits,
    )
    rows = evaluate_donor(payload)
    exclusions = next(row for row in rows if row["_bioetl_frame"] == "exclusions")
    assert exclusions["status"] == "UNKNOWN"
    assert exclusions["detail"] == expected


def test_long_reason_preview_preserves_the_complete_saved_explanation():
    payload = donor_payload(None, None)
    explanation = "Mismatch between saved and current identity. " * 8
    payload["presentation_domains"][0].update(reason_display=explanation)
    rows = evaluate_donor(payload)
    domain = next(row for row in rows if row["_bioetl_frame"] == "domains")
    assert explanation in domain["run_reason"]
    assert domain["reason_display"] == explanation
    assert domain["domain_reason_brief"] == explanation[:31] + "…"
    assert domain["run_reason_brief"] == domain["run_reason"][:19] + "…"
    assert len(domain["run_reason_brief"]) == 20


@pytest.mark.parametrize(
    ("domain_name", "reason", "display"),
    [
        (
            "Workflow",
            "workflow_parent_not_finalized",
            "Parent workflow completion has not been recorded",
        ),
        (
            "Provider",
            "run_preflight_provider_observation",
            "Provider: saved preflight observation",
        ),
    ],
)
def test_run_reason_alias_is_applied_before_bounded_preview(
    domain_name, reason, display
):
    payload = donor_payload(None, None)
    payload["presentation_domains"] = [
        {
            "domain": domain_name,
            "verdict": "INCOMPLETE",
            "reason": reason,
            "reason_display": reason,
        }
    ]
    rows = evaluate_donor(payload)
    domain = next(row for row in rows if row["_bioetl_frame"] == "domains")
    assert domain["run_reason_brief"] == display[:19] + "…"
    assert len(domain["run_reason_brief"]) == 20
    assert domain["run_reason"] == domain_name + ": " + reason
    assert domain["reason_display"] == reason


def test_domain_provider_reason_alias_precedes_bounded_preview():
    payload = donor_payload(None, None)
    reason = "run_preflight_provider_observation"
    payload["presentation_domains"] = [
        {
            "domain": "Provider",
            "verdict": "WARN",
            "reason": reason,
            "reason_display": reason,
        }
    ]
    rows = evaluate_donor(payload)
    domain = next(row for row in rows if row["_bioetl_frame"] == "domains")
    assert domain["domain_reason_brief"] == "Provider preflight check"
    assert domain["verdict"] == "WARN"
    assert domain["reason_display"] == reason
    assert domain["run_reason"] == "Provider: " + reason


@pytest.mark.parametrize("reason", ["workflow_failed", "Parent workflow failed"])
def test_workflow_failure_is_readable_without_changing_the_error_verdict(reason):
    payload = donor_payload(None, None)
    payload["presentation_summary"][0].update(
        verdict="ERROR", execution_state="SUCCESS"
    )
    payload["presentation_domains"] = [
        {
            "domain": "Workflow",
            "verdict": "ERROR",
            "reason": "workflow_failed",
            "reason_display": reason,
        }
    ]
    payload["reconciliation_display"] = [
        {
            "step_id": "reconcile_assay_target",
            "result": "FAILED",
            "meaning": "ValueError: 433 unmatched source rows; mutation blocked",
        }
    ]
    rows = evaluate_donor(payload)
    domain = next(row for row in rows if row["_bioetl_frame"] == "domains")
    failure = next(row for row in rows if row["_bioetl_frame"] == "reconciliation")
    assert domain["run_reason_brief"] == "Workflow failed"
    assert domain["run_verdict"] == "ERROR"
    assert domain["execution_state"] == "SUCCESS"
    assert failure["step_id"] == "reconcile_assay_target"
    assert failure["meaning"] == payload["reconciliation_display"][0]["meaning"]
