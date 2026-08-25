# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""HTTP run-report ops loaders."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

import json
from pathlib import Path

from bioetl.interfaces.http._health_server_observability_routing import (
    _is_unresolved_run_scope,
    _not_found_pipeline_run_report_shell,
    _summary_rows_pipeline_run_report,
    _table_shape_pipeline_run_report,
    _unresolved_pipeline_run_report_shell,
)
from bioetl.interfaces.http._pipeline_run_report_table import (
    _coverage_chip,
    _coverage_fields,
    _excluded_by_contract_count,
    _funnel_gold_and_excluded,
    _parse_grafana_ms,
    _parse_iso_to_ms,
    _removals_summary,
    _scalar_or_json,
    _section_param_value_rows,
    _shape_funnel_rows,
)
from bioetl.interfaces.http.run_report_ops import (
    _normalize_list_owner,
    _safe_segment,
    list_pipeline_run_report_payloads,
    list_workflow_run_report_payloads,
    load_pipeline_run_report_payload,
    load_workflow_run_report_payload,
)


def test_load_pipeline_report(tmp_path: Path) -> None:
    target = (
        tmp_path / "pipeline" / "chembl_activity" / "run1" / "pipeline-run-report.json"
    )
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps({"schema_version": "pipeline_run_report_v1", "ok": True}),
        encoding="utf-8",
    )
    payload = load_pipeline_run_report_payload(
        run_id="run1",
        pipeline_name="chembl_activity",
        root=tmp_path,
    )
    assert payload is not None
    assert payload["schema_version"] == "pipeline_run_report_v1"


def test_load_missing_returns_none(tmp_path: Path) -> None:
    assert load_pipeline_run_report_payload(run_id="missing", root=tmp_path) is None
    assert (
        load_workflow_run_report_payload(workflow_run_id="missing", root=tmp_path)
        is None
    )


def test_load_explicit_workflow_report_missing_file_returns_none(
    tmp_path: Path,
) -> None:
    """An explicit but absent workflow artifact is a normal cache miss."""
    assert (
        load_workflow_run_report_payload(
            workflow_run_id="missing",
            workflow_name="chembl_core",
            root=tmp_path,
        )
        is None
    )


def test_load_workflow_report_rejects_blank_run_id(tmp_path: Path) -> None:
    """Blank selectors must fail closed before any filesystem lookup."""
    assert (
        load_workflow_run_report_payload(
            workflow_run_id=" \t ",
            workflow_name="chembl_core",
            root=tmp_path,
        )
        is None
    )


def test_safe_segment_sanitizes_and_bounds_operator_input() -> None:
    """Operator selectors remain one bounded filesystem segment."""
    assert _safe_segment(" chembl activity ") == "chembl_activity"
    assert _safe_segment("x" * 121) == "x" * 120
    with pytest.raises(ValueError, match="invalid path segment"):
        _safe_segment("   ")


@pytest.mark.parametrize(
    ("raw_name", "expected"),
    [
        (None, None),
        (" \t ", None),
        ("ALL", None),
        ("*", None),
        ("$__all", None),
        ("__all", None),
        (" chembl_activity ", "chembl_activity"),
    ],
)
def test_normalize_list_owner_handles_grafana_all_scope_tokens(
    raw_name: str | None,
    expected: str | None,
) -> None:
    """Grafana all/blank selectors intentionally expand to every owner."""
    assert _normalize_list_owner(raw_name) == expected


def test_list_pipeline_payloads_includes_report_root_diagnostics(
    tmp_path: Path,
) -> None:
    target = (
        tmp_path / "pipeline" / "chembl_assay" / "run1" / "pipeline-run-report.json"
    )
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            {
                "schema_version": "pipeline_run_report_v1",
                "identity": {
                    "run_id": "run1",
                    "pipeline_name": "chembl_assay",
                    "status": "success",
                    "started_at": "2026-08-25T01:00:00Z",
                    "workflow_id": "chembl_baseline",
                    "workflow_run_id": "wf-run-1",
                    "run_type": "backfill",
                },
            }
        ),
        encoding="utf-8",
    )
    payload = list_pipeline_run_report_payloads(
        pipeline_name="chembl_assay",
        limit=5,
        root=tmp_path,
    )
    assert payload["status"] == "ok"
    assert payload["index_state"] == "ok"
    assert payload["count"] == 1
    assert payload["report_root"] == str(tmp_path.as_posix())
    assert payload["marker_status"] in {"healthy", "unhealthy"}
    assert payload["source_identity_status"] in {"healthy", "unhealthy"}
    assert payload["source_identity_state"] in {
        "missing",
        "invalid",
        "foreign",
        "aligned",
    }
    assert "source_identity_resolution_source" in payload
    assert "source_identity_expected" in payload
    assert "source_identity_actual" in payload
    assert payload["items"][0]["run_id"] == "run1"
    assert payload["items"][0]["selected"] == 0
    assert payload["items"][0]["workflow_id"] == "chembl_baseline"
    assert payload["items"][0]["started_at"] == "2026-08-25T01:00:00Z"
    assert payload["items"][0]["workflow_run_id"] == "wf-run-1"
    assert payload["items"][0]["run_type"] == "backfill"

    marked = list_pipeline_run_report_payloads(
        pipeline_name="chembl_assay",
        limit=5,
        root=tmp_path,
        selected_run_id="run1",
    )
    assert marked["items"][0]["selected"] == 1
    ignored = list_pipeline_run_report_payloads(
        pipeline_name="chembl_assay",
        limit=5,
        root=tmp_path,
        selected_run_id="-",
    )
    assert ignored["items"][0]["selected"] == 0


def test_list_workflow_payloads_includes_identity_and_artifact_paths(
    tmp_path: Path,
) -> None:
    target = tmp_path / "workflow" / "chembl_core" / "wf1" / "workflow-run-report.json"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            {
                "schema_version": "workflow_run_report_v1",
                "identity": {
                    "workflow_run_id": "wf1",
                    "workflow_name": "chembl_core",
                    "status": "success",
                    "completed_at": "2026-08-10T00:00:00Z",
                },
            }
        ),
        encoding="utf-8",
    )
    markdown = target.parent / "workflow-run-report.md"
    markdown.write_text("# workflow report\n", encoding="utf-8")

    payload = list_workflow_run_report_payloads(
        workflow_name="chembl_core",
        limit=5,
        root=tmp_path,
    )

    assert payload["status"] == "ok"
    assert payload["index_state"] == "ok"
    assert payload["count"] == 1
    assert payload["report_root"] == str(tmp_path.as_posix())
    assert payload["marker_status"] in {"healthy", "unhealthy"}
    assert payload["items"] == [
        {
            "workflow": "chembl_core",
            "workflow_run_id": "wf1",
            "status": "success",
            "completed_at": "2026-08-10T00:00:00Z",
            "selected": 0,
            "json_path": str(target.as_posix()),
            "markdown_path": str(markdown.as_posix()),
        }
    ]


def test_unresolved_run_id_sentinel_shell_for_grafana() -> None:
    """run_id='-' must not 404; empty shell keeps Run Explorer panels query-clean."""
    assert _is_unresolved_run_scope("-")
    assert _is_unresolved_run_scope(" $__all ")
    assert not _is_unresolved_run_scope("2f68f55b-3689-5e8a-9880-19cf8cbb69ad")
    shell = _unresolved_pipeline_run_report_shell(
        run_id="-",
        pipeline="chembl_activity",
    )
    assert shell["status"] == "unresolved_scope"
    assert shell["funnel"] == []
    assert shell["reasons_top_n"] == []
    assert shell["artifacts"] == []
    assert shell["reconciliation"] == []
    assert shell["layers"] == []
    assert shell["failure"] == []
    assert shell["stage_timings"] == []
    assert shell["identity_rows"] == []
    assert shell["timings_and_failure"] == []


def test_table_shape_pipeline_run_report_reconciliation_rows() -> None:
    shaped = _table_shape_pipeline_run_report(
        {
            "schema_version": "pipeline_run_report_v1",
            "reconciliation": {
                # Deliberately reverse key insertion order (REC-04 stable order).
                "gold_vs_silver_status": "OK",
                "gold_delta": 0,
                "gold_accounted": 1000,
                "silver_vs_bronze_status": "OK",
                "silver_delta": 0,
                "silver_accounted": 10,
            },
            "funnel": [{"stage": "bronze"}],
        }
    )
    assert shaped["reconciliation"] == [
        {"parameter": "silver_accounted", "value": "10"},
        {"parameter": "silver_delta", "value": "0"},
        {"parameter": "silver_vs_bronze_status", "value": "OK"},
        {"parameter": "gold_accounted", "value": "1000"},
        {"parameter": "gold_delta", "value": "0"},
        {"parameter": "gold_vs_silver_status", "value": "OK"},
    ]
    assert shaped["funnel"] == [{"stage": "bronze", "removals_summary": "—"}]
    with_removals = _table_shape_pipeline_run_report(
        {
            "schema_version": "pipeline_run_report_v1",
            "funnel": [
                {
                    "stage_id": "gold",
                    "removals": [
                        {
                            "count": 17,
                            "outcome": "excluded_by_contract",
                            "reason_code": "gold_contract_schema_failure",
                        }
                    ],
                }
            ],
        }
    )
    assert with_removals["funnel"][0]["removals_summary"] == (
        "17 gold_contract_schema_failure"
    )


def test_table_shape_pipeline_run_report_layers_failure_identity() -> None:
    shaped = _table_shape_pipeline_run_report(
        {
            "schema_version": "pipeline_run_report_v1",
            "layers": {"gold_written": 9, "bronze_records": 10},
            "failure": {"failed_stage": "gold", "error_type": "ContractError"},
            "stage_timings": {"extract": 1.5},
            "identity": {"run_id": "abc", "status": "failed"},
            "tracking_coverage": "full",
        }
    )
    assert shaped["layers"][0] == {"parameter": "bronze_records", "value": "10"}
    assert shaped["failure"][0]["parameter"] == "error_type"
    assert shaped["stage_timings"] == [{"parameter": "extract", "value": "1.5"}]
    assert shaped["timings_and_failure"] == [
        {"section": "failure", "parameter": "error_type", "value": "ContractError"},
        {"section": "failure", "parameter": "failed_stage", "value": "gold"},
        {
            "section": "stage_timings",
            "parameter": "extract",
            "value": "1.5",
        },
    ]
    assert {"parameter": "status", "value": "failed"} in shaped["identity_rows"]
    assert {"parameter": "tracking_coverage", "value": "full"} in shaped[
        "identity_rows"
    ]


def test_not_found_pipeline_run_report_shell_for_grafana() -> None:
    """Missing report must stay HTTP-200-friendly for Infinity tables (#7650)."""
    shell = _not_found_pipeline_run_report_shell(
        run_id="missing-run",
        pipeline="chembl_assay",
    )
    assert shell["status"] == "not_found"
    assert shell["reconciliation"] == []
    assert shell["funnel"] == []
    assert shell["artifacts"] == []
    assert shell["layers"] == []
    assert shell["failure"] == []
    assert shell["stage_timings"] == []
    assert shell["identity_rows"] == []
    assert shell["timings_and_failure"] == []


def test_table_shape_always_exposes_infinity_list_keys() -> None:
    """Missing optional blocks must stay empty arrays, not omitted keys (#9373)."""
    shaped = _table_shape_pipeline_run_report(
        {"schema_version": "pipeline_run_report_v1"}
    )
    for key in (
        "failure",
        "stage_timings",
        "identity_rows",
        "layers",
        "funnel",
        "timings_and_failure",
    ):
        assert key in shaped, key
        assert shaped[key] == [], key

    reshaped = _table_shape_pipeline_run_report(
        _not_found_pipeline_run_report_shell(
            run_id="missing-run",
            pipeline="chembl_assay",
        )
    )
    assert reshaped["timings_and_failure"] == []
    assert reshaped["failure"] == []
    assert reshaped["stage_timings"] == []
    assert reshaped["identity_rows"] == []


def test_load_requires_explicit_owner_selector(tmp_path: Path) -> None:
    target = (
        tmp_path / "pipeline" / "chembl_activity" / "run1" / "pipeline-run-report.json"
    )
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps({"schema_version": "pipeline_run_report_v1"}),
        encoding="utf-8",
    )
    assert load_pipeline_run_report_payload(run_id="run1", root=tmp_path) is None


def test_load_rejects_dot_only_path_segments(tmp_path: Path) -> None:
    """Traversal-style segments must not resolve to a loadable path."""
    assert (
        load_pipeline_run_report_payload(
            run_id="..",
            pipeline_name="chembl_activity",
            root=tmp_path,
        )
        is None
    )
    assert (
        load_pipeline_run_report_payload(
            run_id="run1",
            pipeline_name=".",
            root=tmp_path,
        )
        is None
    )


def test_load_malformed_json_returns_none(tmp_path: Path) -> None:
    target = (
        tmp_path / "pipeline" / "chembl_activity" / "run1" / "pipeline-run-report.json"
    )
    target.parent.mkdir(parents=True)
    target.write_text("{not-json", encoding="utf-8")
    assert (
        load_pipeline_run_report_payload(
            run_id="run1",
            pipeline_name="chembl_activity",
            root=tmp_path,
        )
        is None
    )


def test_list_pipeline_run_reports(tmp_path: Path) -> None:
    target = (
        tmp_path / "pipeline" / "chembl_activity" / "run1" / "pipeline-run-report.json"
    )
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(
            {
                "schema_version": "pipeline_run_report_v1",
                "identity": {"run_id": "run1", "status": "success"},
            }
        ),
        encoding="utf-8",
    )
    payload = list_pipeline_run_report_payloads(
        pipeline_name="chembl_activity",
        limit=5,
        root=tmp_path,
    )
    assert payload["count"] == 1
    assert payload["index_state"] == "ok"
    assert payload["items"][0]["run_id"] == "run1"
    assert payload["items"][0]["workflow_id"] == "—"
    assert payload["items"][0]["workflow_run_id"] == "—"
    assert payload["items"][0]["started_at"] is None
    assert payload["items"][0]["run_type"] is None


def test_list_pipeline_run_reports_distinguishes_no_artifacts(
    tmp_path: Path,
) -> None:
    """A missing kind tree is TREE_MISSING, not a backend failure."""
    payload = list_pipeline_run_report_payloads(
        pipeline_name="chembl_activity",
        limit=5,
        root=tmp_path,
    )

    assert payload["status"] == "ok"
    assert payload["count"] == 0
    assert payload["index_state"] == "tree_missing"
    assert payload["items"] == [
        {
            "row_kind": "diagnostic",
            "pipeline": "chembl_activity",
            "run_id": "-",
            "workflow_id": "—",
            "workflow_run_id": "—",
            "status": "TREE_MISSING",
            "started_at": None,
            "run_type": None,
            "completed_at": None,
            "selected": 0,
            "json_path": None,
            "markdown_path": None,
            "message": payload["index_state_message"],
        }
    ]
    assert "verify_report_bind.py" in str(payload["index_state_message"])
    assert payload["report_root"] == str(tmp_path.as_posix())
    assert "marker_status" in payload


def _healthy_index_diagnostics(**_kwargs: object) -> dict[str, str]:
    return {
        "layout_status": "healthy",
        "source_identity_status": "healthy",
        "source_identity_state": "aligned",
        "marker": "ok",
    }


def test_list_pipeline_valid_empty_when_kind_tree_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pipeline").mkdir()
    monkeypatch.setattr(
        "bioetl.interfaces.http.run_report_ops.report_root_readiness_check",
        _healthy_index_diagnostics,
    )
    payload = list_pipeline_run_report_payloads(
        pipeline_name="chembl_activity",
        limit=5,
        root=tmp_path,
    )
    assert payload["status"] == "ok"
    assert payload["count"] == 0
    assert payload["index_state"] == "valid_empty"
    assert payload["items"] == []


def test_list_pipeline_layout_unhealthy_when_marker_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pipeline").mkdir()
    monkeypatch.setattr(
        "bioetl.interfaces.http.run_report_ops.report_root_readiness_check",
        lambda **_kwargs: {
            "layout_status": "unhealthy",
            "layout_message": "Report-root marker missing",
            "source_identity_status": "healthy",
            "marker": "missing",
        },
    )
    payload = list_pipeline_run_report_payloads(
        pipeline_name="chembl_assay",
        limit=5,
        root=tmp_path,
    )
    assert payload["index_state"] == "layout_unhealthy"
    assert payload["count"] == 0
    assert payload["items"][0]["status"] == "LAYOUT_UNHEALTHY"
    assert payload["items"][0]["row_kind"] == "diagnostic"


def test_list_pipeline_identity_unhealthy_when_source_drifts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pipeline").mkdir()
    monkeypatch.setattr(
        "bioetl.interfaces.http.run_report_ops.report_root_readiness_check",
        lambda **_kwargs: {
            "layout_status": "healthy",
            "source_identity_status": "unhealthy",
            "source_identity_message": "foreign source identity",
            "source_identity_state": "foreign",
            "marker": "ok",
        },
    )
    payload = list_pipeline_run_report_payloads(
        pipeline_name="chembl_assay",
        limit=5,
        root=tmp_path,
    )
    assert payload["index_state"] == "identity_unhealthy"
    assert payload["items"][0]["status"] == "IDENTITY_UNHEALTHY"
    assert payload["items"][0]["run_id"] == "-"


def test_list_workflow_tree_missing_emits_diagnostic_row(tmp_path: Path) -> None:
    payload = list_workflow_run_report_payloads(
        workflow_name="chembl_baseline",
        limit=5,
        root=tmp_path,
    )
    assert payload["index_state"] == "tree_missing"
    assert payload["count"] == 0
    assert payload["items"][0]["workflow"] == "chembl_baseline"
    assert payload["items"][0]["workflow_run_id"] == "-"
    assert payload["items"][0]["status"] == "TREE_MISSING"


def test_load_rejects_wrong_schema_version(tmp_path: Path) -> None:
    target = tmp_path / "workflow" / "demo" / "wf1" / "workflow-run-report.json"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps({"schema_version": "pipeline_run_report_v1"}),
        encoding="utf-8",
    )
    assert (
        load_workflow_run_report_payload(
            workflow_run_id="wf1",
            workflow_name="demo",
            root=tmp_path,
        )
        is None
    )


def test_summary_rows_unresolved_and_missing_are_not_ok() -> None:
    unresolved = _summary_rows_pipeline_run_report(
        _unresolved_pipeline_run_report_shell(run_id="-", pipeline="chembl_activity")
    )
    assert unresolved["summary"][0]["covers_selected_run"] == "select_run"
    assert unresolved["status"] == "unresolved_scope"
    missing = _summary_rows_pipeline_run_report(
        _not_found_pipeline_run_report_shell(
            run_id="missing-run", pipeline="chembl_assay"
        )
    )
    assert missing["summary"][0]["covers_selected_run"] == "not_found"
    assert missing["status"] == "not_found"


def test_table_shape_funnel_and_scalar_edge_branches() -> None:
    assert _scalar_or_json(None) == ""
    assert _scalar_or_json(True) == "true"
    assert _scalar_or_json(False) == "false"
    assert json.loads(_scalar_or_json({"b": 1, "a": 2})) == {"a": 2, "b": 1}
    assert _section_param_value_rows("failure", None) == []
    assert _section_param_value_rows("failure", ["skip", {"value": "x"}]) == []
    assert _removals_summary("not-a-list") == "—"
    assert _removals_summary([{"count": 3}, "skip", {"outcome": "dropped"}]) == (
        "dropped"
    )
    assert _removals_summary([{"reason_code": "schema", "count": None}]) == "schema"
    assert _shape_funnel_rows({}) == []
    shaped = _shape_funnel_rows(
        {"funnel": ["bronze", {"stage_id": "gold", "removals": [{"count": 1}]}]}
    )
    assert shaped[0] == "bronze"
    assert shaped[1]["removals_summary"] == "—"

    nested = _table_shape_pipeline_run_report(
        {
            "schema_version": "pipeline_run_report_v1",
            "identity": {"run_id": "abc", "ok": True, "meta": {"k": 1}, "empty": None},
            "funnel": [
                {
                    "stage_id": "gold",
                    "records_out": 9,
                    "removals": [
                        {
                            "count": 2,
                            "outcome": "excluded_by_contract",
                            "reason_code": "gold_contract_schema_failure",
                        },
                        "skip",
                        {"outcome": "other", "count": "n/a"},
                    ],
                }
            ],
        }
    )
    assert {"parameter": "ok", "value": "true"} in nested["identity_rows"]
    assert nested["funnel"][0]["removals_summary"] == (
        "2 gold_contract_schema_failure, n/a other"
    )


def test_summary_rows_coverage_window_and_funnel_helpers() -> None:
    assert _parse_iso_to_ms("") is None
    assert _parse_iso_to_ms("not-iso") is None
    zulu = _parse_iso_to_ms("2026-08-10T00:00:00Z")
    naive = _parse_iso_to_ms("2026-08-10T00:00:00")
    assert zulu is not None and naive is not None
    assert _parse_grafana_ms(None) is None
    assert _parse_grafana_ms("  ") is None
    assert _parse_grafana_ms("abc") is None
    assert _parse_grafana_ms("1000") == 1000
    assert _coverage_chip("yes") == "IN RANGE"
    assert _coverage_chip("outside") == "OUT OF RANGE"
    assert _coverage_chip("partial") == "OUT OF RANGE"
    assert _coverage_chip("unknown") == "UNKNOWN"
    assert _coverage_fields(
        started_ms=None,
        completed_ms=None,
        grafana_from_ms=1,
        grafana_to_ms=2,
        status="ok",
    ) == ("unknown", "")
    assert _coverage_fields(
        started_ms=10,
        completed_ms=20,
        grafana_from_ms=None,
        grafana_to_ms=None,
        status="ok",
    ) == ("range_unspecified", "")
    assert _coverage_fields(
        started_ms=10,
        completed_ms=20,
        grafana_from_ms=0,
        grafana_to_ms=30,
        status="ok",
    ) == ("yes", "0h")
    covers, offset = _coverage_fields(
        started_ms=10,
        completed_ms=20,
        grafana_from_ms=50,
        grafana_to_ms=80,
        status="ok",
    )
    assert covers == "outside"
    assert "before window" in offset
    covers, offset = _coverage_fields(
        started_ms=90,
        completed_ms=100,
        grafana_from_ms=50,
        grafana_to_ms=80,
        status="ok",
    )
    assert covers == "outside"
    assert "after window" in offset
    covers, offset = _coverage_fields(
        started_ms=10,
        completed_ms=90,
        grafana_from_ms=50,
        grafana_to_ms=80,
        status="ok",
    )
    assert covers == "partial"
    assert offset == "overlaps window"
    assert _excluded_by_contract_count("nope") == 0
    assert _excluded_by_contract_count([{"outcome": "excluded_by_contract"}]) == 0
    assert (
        _excluded_by_contract_count(
            [
                "skip",
                {"outcome": "other", "count": 9},
                {"outcome": "excluded_by_contract", "count": 4},
            ]
        )
        == 4
    )
    assert _funnel_gold_and_excluded("nope") == ("", 0)
    gold_out, excluded = _funnel_gold_and_excluded(
        [
            "skip",
            {
                "stage_id": "silver",
                "removals": [{"outcome": "excluded_by_contract", "count": 1}],
            },
            {"stage_id": "gold", "records_out": 4, "removals": []},
        ]
    )
    assert gold_out == 4
    assert excluded == 1

    summary = _summary_rows_pipeline_run_report(
        {
            "schema_version": "pipeline_run_report_v1",
            "identity": {
                "run_id": "run-1",
                "status": "success",
                "started_at": "2026-08-10T00:00:00Z",
                "completed_at": "2026-08-10T01:00:00Z",
            },
            "funnel": [
                {
                    "stage_id": "gold",
                    "records_out": 8,
                    "removals": [
                        {
                            "count": 3,
                            "outcome": "excluded_by_contract",
                            "reason_code": "gold_contract_schema_failure",
                        }
                    ],
                }
            ],
        },
        grafana_from="1754784000000",
        grafana_to="1754787600000",
    )
    row = summary["summary"][0]
    assert row["gold_records_out"] == "8"
    assert row["excluded_by_contract"] == "3"
    assert row["covers_selected_run"] == "outside"
    assert row["coverage_chip"] == "OUT OF RANGE"
