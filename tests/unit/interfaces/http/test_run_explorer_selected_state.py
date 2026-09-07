"""Selected-run UI state and report provenance regressions (#10187/#10190)."""

from __future__ import annotations

import pytest
from types import SimpleNamespace

from bioetl.interfaces.http import _health_server_identity_routing_support as routing
from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope

from bioetl.interfaces.http._pipeline_run_report_table import (
    _not_found_pipeline_run_report_shell,
    _table_shape_pipeline_run_report,
    _unresolved_pipeline_run_report_shell,
)
from bioetl.interfaces.http.control_plane_identity.payload import (
    build_control_plane_identity_evidence_payload,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("key", ["funnel", "reasons_top_n", "artifacts"])
def test_report_selection_missing_and_loaded_empty_are_distinct(key: str) -> None:
    unselected = _table_shape_pipeline_run_report(
        _unresolved_pipeline_run_report_shell(run_id="-", pipeline="chembl_assay")
    )
    missing = _table_shape_pipeline_run_report(
        _not_found_pipeline_run_report_shell(run_id="absent", pipeline="chembl_assay")
    )
    empty = _table_shape_pipeline_run_report({key: []})
    assert "SELECT RUN" in unselected[f"{key}_display"][0].values()
    assert "TELEMETRY MISSING" in missing[f"{key}_display"][0].values()
    assert "VALID EMPTY" in empty[f"{key}_display"][0].values()
    assert unselected[key] == missing[key] == empty[key] == []


@pytest.mark.parametrize("view", ["overview", "copy_values", "gaps", "anchors"])
@pytest.mark.parametrize(
    "run_id,state", [(None, "SELECT RUN"), ("absent", "TELEMETRY MISSING")]
)
def test_unresolved_identity_never_claims_verified_anchors(
    view: str, run_id: str | None, state: str
) -> None:
    result = build_control_plane_identity_evidence_payload(
        requested_pipeline="chembl_assay",
        resolved_manifest=None,
        selected_pipelines=("chembl_assay",),
        selected_run_id=run_id,
        selected_run_types=(),
        resolved_via="selection_required"
        if run_id is None
        else "selected_run_id_not_found",
        ledger_port=None,
        view=view,
    )
    assert result["summary"]["overall_status"] == state
    assert result["rows"]
    assert all(row["ui_status"] == state for row in result["rows"])
    assert all(row["source_quality"] == "unavailable" for row in result["anchors"])


def test_funnel_display_keeps_gold_and_full_exclusion_reason() -> None:
    source = {
        "funnel": [
            {"stage_id": stage, "records_out": count, "removals": []}
            for stage, count in (
                ("extract", 1000),
                ("bronze", 1000),
                ("silver", 1000),
                ("gold", 983),
            )
        ]
    }
    source["funnel"][-1]["removals"] = [
        {"count": 17, "reason_code": "gold_contract_schema_failure"}
    ]
    result = _table_shape_pipeline_run_report(source)
    rows = result["funnel_display"]
    assert [row["stage_id"] for row in rows] == ["extract", "bronze", "silver", "gold"]
    assert rows[-1]["records_out"] == 983
    assert rows[-1]["removals_summary"] == "17 gold_contract_schema_failure"


@pytest.mark.asyncio
@pytest.mark.parametrize("report_run_id", ["selected", "another-run"])
async def test_identity_summary_uses_only_the_selected_report(
    monkeypatch: pytest.MonkeyPatch, report_run_id: str
) -> None:
    monkeypatch.setattr(
        routing,
        "build_control_plane_identity_evidence_payload",
        lambda **kwargs: {"summary": {}},
    )
    monkeypatch.setattr(
        routing,
        "load_pipeline_run_report_payload",
        lambda **kwargs: {
            "identity": {
                "run_id": report_run_id,
                "status": "success",
                "started_at": "2026-09-06T12:20:49+00:00",
                "completed_at": "2026-09-06T12:21:15+00:00",
                "workflow_id": "chembl_baseline",
                "workflow_run_id": "workflow-run",
                "workflow_step_id": "run_chembl_assay",
            },
            "tracking_coverage": "full",
        },
    )
    scope = _IdentityScope(
        requested_pipeline="chembl_assay",
        selected_pipelines=("chembl_assay",),
        selected_run_types=(),
        selected_run_id="selected",
        resolved_manifest=None,
        resolved_via="selected_run_id_not_found",
    )
    summary = await routing._build_identity_evidence_summary(
        SimpleNamespace(_run_ledger_port=None), scope=scope, checkpoint_metadata=None
    )
    if report_run_id == "selected":
        assert summary["run_status"] == "success"
        assert summary["started_at"] == "2026-09-06T12:20:49+00:00"
        assert summary["completed_at"] == "2026-09-06T12:21:15+00:00"
        assert summary["tracking_coverage"] == "full"
        rows = routing.build_control_plane_identity_payload(
            requested_pipeline="chembl_assay",
            resolved_manifest=None,
            selected_pipelines=("chembl_assay",),
            selected_run_id="selected",
            selected_run_types=(),
            resolved_via="selected_run_id_not_found",
            identity_evidence_summary=summary,
        )["rows"]
        values = {row["parameter"]: row["value"] for row in rows}
        assert values["Tracking coverage"] == "full"
        assert values["Workflow ID"] == "chembl_baseline"
        assert values["Workflow Run ID"] == "workflow-run"
        assert values["Workflow Step ID"] == "run_chembl_assay"
    else:
        assert summary == {}
