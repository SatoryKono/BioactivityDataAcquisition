# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for run report query helpers."""

from __future__ import annotations

import json
import os

import pytest

pytestmark = pytest.mark.unit

from datetime import UTC, datetime
from pathlib import Path

from bioetl.application.services.run_reports import query as report_query
from bioetl.application.services.run_reports.query import (
    diff_pipeline_reports,
    list_pipeline_reports,
    list_workflow_reports,
    load_latest_pointer,
    load_pipeline_report,
    load_workflow_report,
    prune_reports,
)
from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.domain.run_reports.models import StageId
from bioetl.domain.run_reports.pipeline_builder import build_pipeline_run_report


def _write_simple(tmp_path: Path, *, run_id: str, silver: int) -> None:
    acc = StageAccountingAccumulator()
    acc.record_in(StageId.SILVER.value, 10)
    acc.record_out(StageId.SILVER.value, silver)
    removed = 10 - silver
    if removed:
        acc.record_removal(
            StageId.SILVER.value,
            outcome="filtered_out",
            reason_code="FILTERED_OUT_SILVER",
            count=removed,
        )
    report = build_pipeline_run_report(
        identity={
            "run_id": run_id,
            "pipeline_name": "chembl_activity",
            "run_type": "incremental",
            "status": "success",
        },
        metrics={
            "records_fetched": 10,
            "records_bronze": 10,
            "records_silver": silver,
            "records_gold": 0,
            "records_filtered_out": removed,
            "records_quarantined": 0,
        },
        accounting=acc,
    )
    write_pipeline_run_report(report, root=tmp_path)


def _write_raw_report(
    root: Path,
    *,
    kind: str,
    owner: str,
    run_id: str,
    payload: object,
    mtime: float,
) -> Path:
    report_path = root / kind / owner / run_id / f"{kind}-run-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    os.utime(report_path, (mtime, mtime))
    return report_path


def test_list_and_latest(tmp_path: Path) -> None:
    _write_simple(tmp_path, run_id="run-a", silver=9)
    _write_simple(tmp_path, run_id="run-b", silver=8)
    entries = list_pipeline_reports(
        pipeline_name="chembl_activity", root=tmp_path, limit=5
    )
    assert len(entries) == 2
    latest = load_pipeline_report(
        pipeline_name="chembl_activity",
        latest=True,
        root=tmp_path,
    )
    assert latest is not None
    assert latest["identity"]["run_id"] == "run-b"


def test_diff_and_prune_dry_run(tmp_path: Path) -> None:
    _write_simple(tmp_path, run_id="run-a", silver=9)
    _write_simple(tmp_path, run_id="run-b", silver=7)
    left = load_pipeline_report(
        pipeline_name="chembl_activity",
        run_id="run-a",
        root=tmp_path,
    )
    right = load_pipeline_report(
        pipeline_name="chembl_activity",
        run_id="run-b",
        root=tmp_path,
    )
    assert left is not None and right is not None
    delta = diff_pipeline_reports(left, right)
    assert "funnel_delta" in delta
    assert "reasons_delta" in delta
    victims = prune_reports(
        kind="pipeline",
        owner="chembl_activity",
        max_count=1,
        root=tmp_path,
        dry_run=True,
    )
    assert len(victims) == 1


def test_prune_by_age_uses_explicit_time_seam(tmp_path: Path) -> None:
    _write_simple(tmp_path, run_id="run-a", silver=9)

    victims = prune_reports(
        kind="pipeline",
        owner="chembl_activity",
        max_age_days=1,
        now=datetime(2100, 1, 1, tzinfo=UTC),
        root=tmp_path,
        dry_run=True,
    )

    assert len(victims) == 1


def test_load_helpers_handle_absent_non_mapping_and_invalid_json(
    tmp_path: Path,
) -> None:
    assert list_pipeline_reports(root=tmp_path) == []
    assert load_latest_pointer(kind="pipeline", owner="missing", root=tmp_path) is None
    assert (
        load_pipeline_report(
            pipeline_name="missing",
            run_id="run-1",
            root=tmp_path,
        )
        is None
    )
    assert load_pipeline_report(pipeline_name="missing", root=tmp_path) is None

    owner_dir = tmp_path / "pipeline" / "chembl_activity"
    owner_dir.mkdir(parents=True)
    pointer_path = owner_dir / "_latest.json"
    pointer_path.write_text("[]", encoding="utf-8")
    assert (
        load_latest_pointer(
            kind="pipeline",
            owner="chembl_activity",
            root=tmp_path,
        )
        is None
    )

    pointer_path.write_text("{invalid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_latest_pointer(
            kind="pipeline",
            owner="chembl_activity",
            root=tmp_path,
        )

    pointer_path.unlink()
    report_path = _write_raw_report(
        tmp_path,
        kind="pipeline",
        owner="chembl_activity",
        run_id="run-1",
        payload=[],
        mtime=100.0,
    )
    assert (
        load_pipeline_report(
            pipeline_name="chembl_activity",
            run_id="run-1",
            root=tmp_path,
        )
        is None
    )

    report_path.write_text("{invalid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_pipeline_report(
            pipeline_name="chembl_activity",
            run_id="run-1",
            root=tmp_path,
        )


def test_workflow_report_loads_direct_and_latest_targets(tmp_path: Path) -> None:
    report_path = _write_raw_report(
        tmp_path,
        kind="workflow",
        owner="nightly",
        run_id="workflow-1",
        payload={"identity": {"run_id": "workflow-1"}},
        mtime=100.0,
    )
    pointer_path = tmp_path / "workflow" / "nightly" / "_latest.json"
    pointer_path.write_text(
        json.dumps({"json_path": str(report_path)}),
        encoding="utf-8",
    )

    direct = load_workflow_report(
        workflow_name="nightly",
        workflow_run_id="workflow-1",
        root=tmp_path,
    )
    implicit_latest = load_workflow_report(workflow_name="nightly", root=tmp_path)
    explicit_latest = load_workflow_report(
        workflow_name="nightly",
        workflow_run_id="ignored",
        latest=True,
        root=tmp_path,
    )

    assert direct == implicit_latest == explicit_latest
    pointer_path.write_text("{}", encoding="utf-8")
    assert load_workflow_report(workflow_name="nightly", root=tmp_path) is None


def test_listing_filters_entries_sorts_by_mtime_and_honors_limits(
    tmp_path: Path,
) -> None:
    old_path = _write_raw_report(
        tmp_path,
        kind="pipeline",
        owner="owner-a",
        run_id="run-old",
        payload={"identity": {"status": True, "completed_at": 123}},
        mtime=100.0,
    )
    old_path.with_suffix(".md").write_text("old", encoding="utf-8")
    invalid_path = _write_raw_report(
        tmp_path,
        kind="pipeline",
        owner="owner-a",
        run_id="run-middle",
        payload={},
        mtime=200.0,
    )
    invalid_path.write_text("{invalid", encoding="utf-8")
    os.utime(invalid_path, (200.0, 200.0))
    newest_path = _write_raw_report(
        tmp_path,
        kind="pipeline",
        owner="owner-b",
        run_id="run-new",
        payload=[],
        mtime=300.0,
    )

    pipeline_root = tmp_path / "pipeline"
    (pipeline_root / "README.txt").write_text("not an owner", encoding="utf-8")
    owner_dir = pipeline_root / "owner-a"
    (owner_dir / "stray.txt").write_text("not a run", encoding="utf-8")
    (owner_dir / ".partial").mkdir()
    (owner_dir / ".partial" / "pipeline-run-report.json").write_text(
        "{}", encoding="utf-8"
    )
    (owner_dir / "missing-report").mkdir()

    entries = list_pipeline_reports(root=tmp_path, limit=2)
    assert [entry.run_id for entry in entries] == ["run-new", "run-middle"]
    assert entries[0].json_path == newest_path
    assert entries[0].status is None
    assert entries[0].completed_at is None

    owner_entries = list_pipeline_reports(
        pipeline_name="owner-a", root=tmp_path, limit=10
    )
    assert [entry.run_id for entry in owner_entries] == ["run-middle", "run-old"]
    assert owner_entries[0].markdown_path is None
    assert owner_entries[0].status is None
    assert owner_entries[1].markdown_path == old_path.with_suffix(".md")
    assert owner_entries[1].status == "True"
    assert owner_entries[1].completed_at == "123"
    assert list_pipeline_reports(root=tmp_path, limit=-1) == []
    assert (
        list_pipeline_reports(
            pipeline_name="owner-that-does-not-exist",
            root=tmp_path,
        )
        == []
    )


def test_diff_handles_sparse_rows_and_numeric_coercion() -> None:
    left = {
        "funnel": [
            {
                "stage_id": "silver",
                "records_in": "10",
                "records_out": b"8",
                "removed_total": object(),
            },
            {"stage_id": "left-only", "records_in": float("inf")},
            "not-a-row",
        ],
        "reasons_top_n": [
            {"reason_code": "A", "count": "2"},
            {"reason_code": "B", "count": object()},
            "not-a-row",
        ],
    }
    right = {
        "identity": {"run_id": "right"},
        "funnel": [
            {
                "stage_id": "silver",
                "records_in": 13.9,
                "records_out": 9.9,
                "removed_total": "invalid",
            },
            {"stage_id": "right-only", "records_in": 3},
        ],
        "reasons_top_n": [
            {"reason_code": "B", "count": 5},
            {"reason_code": "C", "count": bytearray(b"4")},
        ],
    }

    assert diff_pipeline_reports(left, right) == {
        "left_run_id": None,
        "right_run_id": "right",
        "funnel_delta": [
            {
                "stage_id": "left-only",
                "records_in_delta": 0,
                "records_out_delta": 0,
                "removed_total_delta": 0,
            },
            {
                "stage_id": "right-only",
                "records_in_delta": 3,
                "records_out_delta": 0,
                "removed_total_delta": 0,
            },
            {
                "stage_id": "silver",
                "records_in_delta": 3,
                "records_out_delta": 1,
                "removed_total_delta": 0,
            },
        ],
        "reasons_delta": [
            {"reason_code": "A", "count_delta": -2},
            {"reason_code": "B", "count_delta": 5},
            {"reason_code": "C", "count_delta": 4},
        ],
    }

    with pytest.raises(TypeError, match="report payload must be a mapping"):
        diff_pipeline_reports([], {})
    with pytest.raises(TypeError, match="report payload must be a mapping"):
        diff_pipeline_reports({}, [])


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"kind": "unknown", "max_count": 1}, "kind must be"),
        ({"kind": "pipeline"}, "provide max_count"),
        (
            {"kind": "pipeline", "max_age_days": 1},
            "now is required",
        ),
    ],
)
def test_prune_rejects_invalid_options(
    tmp_path: Path,
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        prune_reports(root=tmp_path, **kwargs)


def test_workflow_prune_removes_recursive_duplicate_candidate_once(
    tmp_path: Path,
) -> None:
    old_path = _write_raw_report(
        tmp_path,
        kind="workflow",
        owner="nightly",
        run_id="old",
        payload={"identity": {"status": "failed"}},
        mtime=100.0,
    )
    nested = old_path.parent / "artifacts" / "nested"
    nested.mkdir(parents=True)
    (nested / "evidence.txt").write_text("evidence", encoding="utf-8")
    new_path = _write_raw_report(
        tmp_path,
        kind="workflow",
        owner="nightly",
        run_id="new",
        payload={"identity": {"status": "success"}},
        mtime=300.0,
    )

    removed = prune_reports(
        kind="workflow",
        owner="nightly",
        max_count=1,
        max_age_days=0,
        now=datetime.fromtimestamp(200, tz=UTC),
        root=tmp_path,
        dry_run=False,
    )

    assert removed == [old_path.parent.as_posix()]
    assert not old_path.parent.exists()
    assert new_path.is_file()
    assert [entry.run_id for entry in list_workflow_reports(root=tmp_path)] == ["new"]


def test_identity_metadata_handles_os_error_and_non_mapping_payloads(
    tmp_path: Path,
) -> None:
    assert report_query._read_identity_meta(tmp_path) == (None, None)

    payload_path = tmp_path / "report.json"
    payload_path.write_text("[]", encoding="utf-8")
    assert report_query._read_identity_meta(payload_path) == (None, None)

    payload_path.write_text('{"identity": "invalid"}', encoding="utf-8")
    assert report_query._read_identity_meta(payload_path) == (None, None)
