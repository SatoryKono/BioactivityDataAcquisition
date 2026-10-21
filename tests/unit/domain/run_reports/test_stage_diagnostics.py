"""Saved-run stage diagnostics do not invent counts or read clocks."""

from __future__ import annotations

import pytest

from bioetl.domain.run_reports.stage_diagnostics import project_stage_diagnostics

pytestmark = pytest.mark.unit


def test_absent_report_never_invents_stage_success():
    payload = project_stage_diagnostics(None)
    assert payload["diagnostic_coverage"] == "INCOMPLETE"
    assert payload["stage_diagnostics"][0]["reason"] == "terminal_event_missing"


def test_unknown_balance_and_malformed_counts_remain_unconfirmed():
    payload = project_stage_diagnostics(
        {
            "identity": {"status": "success"},
            "funnel": [
                {
                    "stage_id": "silver",
                    "balance_status": "future-status",
                    "records_in": True,
                    "records_out": "4",
                }
            ],
            "stage_timings": {
                "silver": {"duration_seconds": True},
                "gold": "unmeasured",
            },
        },
        ledger_events=[
            {"event_type": "unrelated"},
            {"event_type": "stage_started", "stage_id": "bronze", "records_in": False},
            {"event_type": "stage_completed", "stage_id": "silver"},
        ],
    )
    rows = {row["stage_id"]: row for row in payload["stage_diagnostics"]}
    assert rows["silver"]["reason"] == "stage_balance_unknown"
    assert rows["silver"]["records_in"] is None
    assert rows["silver"]["records_out"] is None
    assert rows["silver"]["duration_seconds"] is None
    assert rows["gold"]["duration_seconds"] is None
    assert rows["bronze"]["state"] == "UNFINISHED"
    assert payload["diagnostic_coverage"] == "INCOMPLETE"


def test_success_with_balanced_funnel_keeps_zero_and_coverage() -> None:
    payload = project_stage_diagnostics(
        {
            "identity": {"status": "success"},
            "funnel": [
                {
                    "stage_id": "silver",
                    "records_in": 2,
                    "records_out": 0,
                    "balance_status": "OK",
                }
            ],
            "stage_timings": {"silver": {"duration_seconds": 1.5}},
        }
    )
    row = payload["stage_diagnostics"][0]
    assert row["records_out"] == 0
    assert row["state"] == "OK"
    assert row["duration_seconds"] == 1.5
    assert payload["diagnostic_coverage"] == "COMPLETE"
    assert payload["diagnostic_blockers"] == []


def test_success_without_stages_stays_incomplete() -> None:
    payload = project_stage_diagnostics({"identity": {"status": "success"}})
    assert payload["diagnostic_coverage"] == "INCOMPLETE"
    assert payload["stage_diagnostics"][0]["state"] == "INCOMPLETE"
    assert payload["stage_diagnostics"][0]["reason"] == "stage_evidence_missing"
    assert payload["stage_diagnostics"][0]["records_in"] is None


def test_open_run_without_terminal_event_is_unfinished() -> None:
    payload = project_stage_diagnostics({"identity": {"status": "running"}})
    assert payload["stage_diagnostics"][0]["state"] == "UNFINISHED"
    assert payload["stage_diagnostics"][0]["reason"] == "terminal_event_missing"


def test_timing_without_counts_does_not_become_ok() -> None:
    payload = project_stage_diagnostics(
        {
            "identity": {"status": "success"},
            "stage_timings": {"extract": 3},
        }
    )
    row = payload["stage_diagnostics"][0]
    assert row["stage_id"] == "extract"
    assert row["state"] == "INCOMPLETE"
    assert row["records_in"] is None
    assert row["duration_seconds"] == 3


def test_ledger_stage_completed_is_used_when_funnel_is_absent() -> None:
    payload = project_stage_diagnostics(
        {"identity": {"status": "success"}},
        ledger_events=(
            {
                "event_type": "stage_completed",
                "stage": "bronze",
                "records_in": 4,
                "records_out": 4,
            },
        ),
    )
    row = payload["stage_diagnostics"][0]
    assert row["stage_id"] == "bronze"
    assert row["state"] == "OK"
    assert row["source"] == "ledger"


def test_request_state_does_not_invent_a_stage() -> None:
    payload = project_stage_diagnostics(
        None, request_state="SELECT RUN", request_reason="selection_required"
    )
    assert payload["stage_diagnostics"][0]["state"] == "SELECT RUN"
    assert payload["diagnostic_blockers"]
