"""Selected-run accounting and reconciliation applicability stay in the domain."""

from __future__ import annotations

import pytest

from bioetl.domain.run_reports.selected_status import (
    RULES_VERSION,
    accounting_conflicts,
    parent_binding_gap,
    resolve_child_workflow_binding,
    saved_trust_fields,
)

pytestmark = pytest.mark.unit


def test_accounting_conflict_overrides_trust_and_keeps_saved_verdict() -> None:
    conflicts = accounting_conflicts(
        {"silver_vs_bronze_status": "FAILING", "silver_delta": -154},
        "OK",
    )
    projected = saved_trust_fields(
        verdict="OK",
        reasons_text="checked",
        reconciliation={"silver_vs_bronze_status": "FAILING", "silver_delta": -154},
    )
    assert conflicts
    assert "delta=-154" in conflicts[0]
    assert projected["saved_trust_status"] == "OK"
    assert projected["trust_status"] == "ERROR"
    assert projected["accounting_integrity"] == "CONFLICT"
    assert RULES_VERSION == "selected-run-v2"


def test_failing_funnel_overrides_trust_when_coarse_balance_is_clean() -> None:
    projected = saved_trust_fields(
        verdict="OK",
        reasons_text="checked",
        reconciliation={"silver_vs_bronze_status": "DEGRADED", "silver_delta": 1},
        funnel=[
            {
                "stage_id": "silver",
                "balance_status": "FAILING",
                "unaccounted": 1,
            }
        ],
    )
    assert projected["trust_status"] == "ERROR"
    assert projected["saved_trust_status"] == "OK"
    assert projected["accounting_integrity"] == "CONFLICT"
    assert "unaccounted=1" in str(projected["reasons_text"])


def test_clean_accounting_does_not_override_trust() -> None:
    projected = saved_trust_fields(
        verdict="OK",
        reasons_text="checked",
        reconciliation={"silver_vs_bronze_status": "OK", "gold_vs_silver_status": "OK"},
    )
    assert projected["trust_status"] == "OK"
    assert projected["accounting_integrity"] == "NO REPORTED CONFLICT"
    assert projected["reasons_text"] == "checked"


def test_child_binding_gap_codes() -> None:
    assert (
        resolve_child_workflow_binding(None, {"run_id": "r"}, "step")
        == "binding_not_recorded"
    )
    assert (
        resolve_child_workflow_binding("not-a-binding", {"run_id": "r"}, "step")
        == "binding_not_recorded"
    )
    assert (
        resolve_child_workflow_binding({}, {"run_id": "r"}, "step")
        == "identity_not_recorded"
    )
    parent = {"workflow_name": "wf", "workflow_run_id": "wr"}
    assert (
        resolve_child_workflow_binding(parent, {"run_id": "r"}, "step")
        == "child_identity_not_recorded"
    )
    assert (
        resolve_child_workflow_binding(
            parent,
            {"run_id": "r", "pipeline_name": "pipe"},
            None,
        )
        == "child_identity_not_recorded"
    )


def test_parent_binding_requires_exact_child_step() -> None:
    assert (
        parent_binding_gap(
            workflow_name="wf",
            workflow_run_id="wr",
            parent_identity={"workflow_name": "wf", "workflow_run_id": "other"},
            parent_execution=[],
            step_id="s",
            child_run_id="r",
            child_pipeline_name="chembl_activity",
        )
        == "identity_mismatch"
    )
    assert (
        parent_binding_gap(
            workflow_name="wf",
            workflow_run_id="wr",
            parent_identity={"workflow_name": "wf", "workflow_run_id": "wr"},
            parent_execution=[
                {
                    "step_id": "s",
                    "pipeline_run_id": "r",
                    "pipeline_name": "chembl_activity",
                }
            ],
            step_id="s",
            child_run_id="r",
            child_pipeline_name="chembl_activity",
        )
        is None
    )
