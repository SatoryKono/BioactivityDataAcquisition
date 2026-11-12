"""Exercise the complete shared donor, including missing and offset dates."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.ops.observability.grafana.apply_phase25_srs_prr_budget import _OV_DONOR

pytestmark = pytest.mark.unit


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


def evaluate_donor(payload, *, expression=_OV_DONOR):
    node = shutil.which("node")
    module = os.environ.get("JSONATA_MODULE")
    if not node or not module or not Path(module).exists():
        pytest.skip("Set JSONATA_MODULE to exercise the real JSONata engine")
    checked_clock = datetime(2026, 11, 11, 10, tzinfo=UTC)
    script = "const fs=require('fs'); const q=JSON.parse(fs.readFileSync(0,'utf8')); const expr=require(q.module)(q.expr); expr.registerFunction('now',()=>q.now); expr.registerFunction('millis',()=>q.millis); expr.evaluate(q.payload).then(x=>process.stdout.write(JSON.stringify(x))).catch(e=>{console.error(e.message);process.exit(1)});"
    result = subprocess.run(
        [node, "-e", script],
        input=json.dumps(
            {
                "module": module,
                "expr": expression.replace("${run_id:percentencode}", "-"),
                "payload": payload,
                "now": checked_clock.isoformat(),
                "millis": checked_clock.timestamp() * 1000,
            }
        ),
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    return json.loads(result.stdout)


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
    ("reason", "expected"),
    [
        (
            "cached_bronze_no_remote_probe",
            "Cached Bronze used; provider API was not called",
        ),
        ("run_preflight_provider_observation", "Saved provider preflight check"),
    ],
)
def test_provider_reason_is_evaluated_copy_and_report_link_is_preserved(
    reason, expected
):
    payload = donor_payload("2026-11-11T10:00:00Z", "2026-11-11T10:01:00Z")
    payload.update(
        evidence_availability="AVAILABLE",
        presentation_domains=[{"domain": "Provider", "reason": reason}],
    )
    row = next(r for r in evaluate_donor(payload) if r["_bioetl_frame"] == "provider")
    assert row["reason"] == expected
    assert row["report_label"] == "Open report"


@pytest.mark.parametrize(
    ("selected_id", "returned_id"),
    [("-", "unrelated-run"), ("selected-run", "unrelated-run"), ("-", "-")],
)
def test_dq_stage_input_rejects_fallback_and_mismatched_runs(selected_id, returned_id):
    expression = _stage_input_expression(selected_id)
    rows = evaluate_donor(
        {
            "run_id": returned_id,
            "quality_evidence": {"funnel": [{"stage_id": "bronze", "records_in": 777}]},
        },
        expression=expression,
    )
    assert rows == [], "A missing selection must not borrow another run's counts"


def _stage_input_expression(selected_id):
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-dq-v2.json").read_text(encoding="utf-8")
    )
    panel = next(p for p in dashboard["panels"] if p["id"] == 9403)
    target = next(t for t in panel["targets"] if t["refId"] == "StageInput")
    return target["root_selector"].replace(
        "${selected_run_id:percentencode}", selected_id
    )


def test_dq_stage_input_preserves_zero_and_missing_evidence_for_the_selected_run():
    rows = evaluate_donor(
        {
            "run_id": "selected-run",
            "quality_evidence": {"funnel": [{"stage_id": "bronze", "records_in": 0}]},
        },
        expression=_stage_input_expression("selected-run"),
    )
    by_parameter = {row["parameter"]: row for row in rows}
    assert len(rows) == 9
    assert by_parameter["01 bronze_records"]["count in"] == 0
    assert "count in" not in by_parameter["02 silver_valid_records"]
    assert "count in" not in by_parameter["07 gold_written_records"]
