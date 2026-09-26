"""Selected-run UI state and report provenance regressions (#10187/#10190)."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from threading import BoundedSemaphore, Event
from types import SimpleNamespace

import pytest

from bioetl.interfaces.http import _health_server_identity_routing_support as routing
from bioetl.interfaces.http import _health_server_identity_support as identity_support
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


@pytest.fixture
def isolated_identity_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[ThreadPoolExecutor]:
    with ThreadPoolExecutor(max_workers=2) as executor:
        monkeypatch.setattr(routing, "_IDENTITY_SUMMARY_EXECUTOR", executor)
        monkeypatch.setattr(routing, "_IDENTITY_SUMMARY_SLOTS", BoundedSemaphore(2))
        monkeypatch.setattr(routing, "_IDENTITY_EVIDENCE_BUILD_TIMEOUT_SECONDS", 0.05)
        yield executor


def test_partial_identity_keeps_contract_reference_and_unknown_gap_count() -> None:
    assert (
        identity_support._contract_schema({"contract_ref": "gold.assay"})
        == "gold.assay"
    )
    assert identity_support._identity_health(
        {}, {"identity_graph_complete": False}
    ) == ("Incomplete [0 gaps]")


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
    if key == "artifacts":
        for payload in (unselected, missing, empty):
            row = payload["artifacts_display"][0]
            assert "state" in row
            assert not {"kind", "name", "ref"}.intersection(row)


def test_reasons_display_keeps_code_and_adds_operator_label() -> None:
    shaped = _table_shape_pipeline_run_report(
        {
            "reasons_top_n": [
                {
                    "reason_code": "gold_contract_schema_failure",
                    "outcome": "excluded_by_contract",
                    "count": 17,
                }
            ]
        }
    )
    row = shaped["reasons_top_n_display"][0]
    assert row["reason_code"] == "gold_contract_schema_failure"
    assert row["reason_label"] == (
        "Excluded by Gold schema contract (gold_contract_schema_failure)"
    )
    assert row["explain"] == "Open Data Quality"
    assert (
        "17 Excluded by Gold schema contract"
        in _table_shape_pipeline_run_report(
            {
                "funnel": [
                    {
                        "stage_id": "gold",
                        "removals": [
                            {
                                "reason_code": "gold_contract_schema_failure",
                                "outcome": "excluded_by_contract",
                                "count": 17,
                            }
                        ],
                    }
                ]
            }
        )["funnel"][0]["removals_summary"]
    )


def test_reasons_and_artifacts_display_skip_non_dict_items() -> None:
    shaped = _table_shape_pipeline_run_report(
        {
            "reasons_top_n": [
                "skip",
                {"reason_code": "gold_contract_schema_failure", "count": 2},
            ],
            "artifacts": [
                "skip",
                {"kind": "pipeline_run_report_json", "ref": "/tmp/report.json"},
            ],
        }
    )
    assert len(shaped["reasons_top_n_display"]) == 1
    assert shaped["reasons_top_n_display"][0]["reason_code"] == (
        "gold_contract_schema_failure"
    )
    assert len(shaped["artifacts_display"]) == 1
    assert shaped["artifacts_display"][0]["format"] == "pipeline_run_report_json"


def test_artifacts_display_uses_operator_titles_and_keeps_ref() -> None:
    ref = "/data/reports/pipeline/chembl_assay/run-1/pipeline-run-report.json"
    shaped = _table_shape_pipeline_run_report(
        {
            "artifacts": [
                {"kind": "pipeline_run_report_json", "ref": ref},
                {"kind": "pipeline_run_report_md", "ref": ref.replace(".json", ".md")},
            ]
        }
    )
    rows = shaped["artifacts_display"]
    assert [row["title"] for row in rows] == [
        "Report JSON",
        "Readable Markdown report",
    ]
    assert [row["action"] for row in rows] == ["Download", "Open"]
    assert rows[0]["ref"] == ref
    assert rows[0]["format"] == "pipeline_run_report_json"


@pytest.mark.parametrize(
    "view", ["overview", "copy_values", "gaps", "anchors", "checkpoint_compare"]
)
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
    if view == "checkpoint_compare":
        row = result["rows"][0]
        assert row["anchor"] == "Run identity"
        assert row["status"] == state
        assert row["source_type"] == "checkpoint_metadata_compare"
        assert row["source_quality"] == "unavailable"
        assert row["drilldown_target"] == "checkpoint.compare:Run identity"


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
    assert rows[-1]["removals_summary"] == (
        "17 Excluded by Gold schema contract (gold_contract_schema_failure)"
    )


@pytest.mark.parametrize(
    "key,row",
    [
        ("reasons_top_n", {"reason_code": "gold_contract_schema_failure", "count": 17}),
        ("artifacts", {"kind": "gold", "path": "data/output/gold/chembl/assay"}),
    ],
)
def test_loaded_report_display_preserves_reason_and_artifact_fields(
    key: str, row: dict[str, str | int]
) -> None:
    result = _table_shape_pipeline_run_report({key: [row]})
    assert result[key] == [row]
    display_row = result[f"{key}_display"][0]
    assert display_row.items() >= row.items()
    if key == "reasons_top_n":
        assert display_row["reason_label"] == (
            "Excluded by Gold schema contract (gold_contract_schema_failure)"
        )
        assert display_row["explain"] == "Open Data Quality"
    else:
        assert display_row["title"] == "gold"
        assert display_row["action"] == "Open"
        assert display_row["format"] == "gold"


@pytest.mark.asyncio
@pytest.mark.parametrize("report_run_id", ["selected", "another-run"])
@pytest.mark.parametrize("report_pipeline", ["chembl_assay", "chembl_activity"])
@pytest.mark.parametrize(
    "identity_coverage,expected_coverage", [(None, "full"), (0, 0)]
)
async def test_identity_summary_uses_only_the_selected_report(
    monkeypatch: pytest.MonkeyPatch,
    report_run_id: str,
    report_pipeline: str,
    identity_coverage: int | None,
    expected_coverage: str | int,
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
                "pipeline_name": report_pipeline,
                "status": "success",
                "started_at": "2026-09-06T12:20:49+00:00",
                "completed_at": "2026-09-06T12:21:15+00:00",
                "workflow_id": "chembl_baseline",
                "workflow_run_id": "workflow-run",
                "workflow_step_id": "run_chembl_assay",
                "tracking_coverage": identity_coverage,
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
    if report_run_id == "selected" and report_pipeline == "chembl_assay":
        assert summary["run_status"] == "success"
        assert summary["started_at"] == "2026-09-06T12:20:49+00:00"
        assert summary["completed_at"] == "2026-09-06T12:21:15+00:00"
        assert summary["tracking_coverage"] == expected_coverage
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
        assert values["Tracking coverage"] == str(expected_coverage)
        assert values["Workflow ID"] == "chembl_baseline"
        assert values["Workflow Run ID"] == "workflow-run"
        assert values["Workflow Step ID"] == "run_chembl_assay"
    else:
        assert summary == {}


@pytest.mark.asyncio
async def test_slow_report_enrichment_preserves_completed_identity_evidence(
    monkeypatch: pytest.MonkeyPatch,
    isolated_identity_executor: ThreadPoolExecutor,
) -> None:
    release = Event()

    def slow_report(scope: _IdentityScope) -> dict[str, object]:
        release.wait(2)
        return {}

    monkeypatch.setattr(routing, "_selected_report_summary", slow_report)
    monkeypatch.setattr(
        routing,
        "build_control_plane_identity_evidence_payload",
        lambda **kwargs: {"summary": {"identity_graph_complete": True, "gap_count": 0}},
    )
    scope = _IdentityScope(
        requested_pipeline="chembl_assay",
        selected_pipelines=("chembl_assay",),
        selected_run_types=(),
        selected_run_id="selected",
        resolved_manifest=None,
        resolved_via="selected_run_id_not_found",
    )
    try:
        summary = await routing._build_identity_evidence_summary(
            SimpleNamespace(_run_ledger_port=None),
            scope=scope,
            checkpoint_metadata=None,
        )
        assert summary == {"identity_graph_complete": True, "gap_count": 0}
    finally:
        release.set()


@pytest.mark.asyncio
async def test_timed_out_reads_keep_capacity_and_leave_default_executor_available(
    isolated_identity_executor: ThreadPoolExecutor,
) -> None:
    release = Event()
    started: list[int] = []
    asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(max_workers=1))

    def slow_read() -> dict[str, object]:
        started.append(1)
        release.wait(3)
        return {}

    try:
        for _ in range(3):
            results = await asyncio.gather(
                *(routing._bounded_identity_summary(slow_read) for _ in range(6))
            )
            assert results == [None] * 6
        assert len(started) == 2
        assert (
            await asyncio.wait_for(asyncio.to_thread(lambda: "healthy"), 0.5)
            == "healthy"
        )
        release.set()
        assert await routing._bounded_identity_summary(lambda: {"recovered": True}) == {
            "recovered": True
        }
    finally:
        release.set()


@pytest.mark.asyncio
async def test_identity_executor_preserves_request_context(
    isolated_identity_executor: ThreadPoolExecutor,
) -> None:
    request_id = ContextVar("identity_request_id", default="missing")
    token = request_id.set("selected-request")
    try:
        assert await routing._bounded_identity_summary(
            lambda: {"request_id": request_id.get()}
        ) == {"request_id": "selected-request"}
    finally:
        request_id.reset(token)


@pytest.mark.asyncio
async def test_identity_executor_submission_failure_releases_capacity(
    isolated_identity_executor: ThreadPoolExecutor,
) -> None:
    isolated_identity_executor.shutdown()
    with pytest.raises(RuntimeError):
        await routing._bounded_identity_summary(lambda: {})
    slots = routing._IDENTITY_SUMMARY_SLOTS
    assert slots.acquire(blocking=False)
    assert slots.acquire(blocking=False)
    assert not slots.acquire(blocking=False)
    slots.release()
    slots.release()
