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
"""Unit tests for run report filesystem writers."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

import json
from pathlib import Path

from bioetl.application.services.run_reports import writer as run_report_writer
from bioetl.application.services.run_reports.writer import (
    write_json,
    write_pipeline_run_report,
    write_workflow_run_report,
)
from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.domain.run_reports.models import StageId
from bioetl.domain.run_reports.pipeline_builder import (
    PipelineRunReportOptionalBlocks,
    build_pipeline_run_report,
)
from bioetl.domain.run_reports.workflow_builder import build_workflow_run_report


def test_write_pipeline_run_report(tmp_path: Path) -> None:
    acc = StageAccountingAccumulator()
    acc.record_in(StageId.SILVER.value, 10)
    acc.record_out(StageId.SILVER.value, 8)
    acc.record_removal(
        StageId.SILVER.value,
        outcome="filtered_out",
        reason_code="FILTERED_OUT_SILVER",
        count=2,
    )
    report = build_pipeline_run_report(
        identity={
            "run_id": "abc",
            "pipeline_name": "chembl_activity",
            "run_type": "incremental",
            "status": "success",
            "started_at": "2026-07-24T00:00:00+00:00",
            "duration_seconds": 12.5,
            "provider": "chembl",
            "entity": "activity",
        },
        metrics={
            "records_fetched": 10,
            "records_bronze": 10,
            "records_silver": 8,
            "records_gold": 0,
            "records_filtered_out": 2,
            "records_quarantined": 0,
        },
        accounting=acc,
        optional_blocks=PipelineRunReportOptionalBlocks(
            schema_versions={
                "reason_catalog_version": "reason_catalog_v1",
                "bioetl_version": "6.1.0",
            },
        ),
    )
    written = write_pipeline_run_report(report, root=tmp_path)
    assert written.json_path.is_file()
    assert written.markdown_path.is_file()
    assert written.latest_path is not None and written.latest_path.is_file()
    payload = json.loads(written.json_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "pipeline_run_report_v1"
    kinds = {item["kind"] for item in payload["artifacts"]}
    assert "pipeline_run_report_json" in kinds
    assert "pipeline_run_report_md" in kinds
    latest = json.loads(written.latest_path.read_text(encoding="utf-8"))
    assert latest["run_id"] == "abc"
    md = written.markdown_path.read_text(encoding="utf-8")
    assert "Funnel" in md
    assert "duration_seconds" in md
    assert "Artifacts" in md
    assert "bronze" in md.lower() or "Bronze" in md


def test_write_workflow_run_report(tmp_path: Path) -> None:
    report = build_workflow_run_report(
        identity={
            "workflow_name": "demo_wf",
            "workflow_run_id": "wf1",
            "status": "success",
        },
        plan_steps=[
            {
                "step_id": "s1",
                "kind": "pipeline",
                "pipeline_name": "chembl_activity",
                "depends_on": [],
            }
        ],
        execution_steps=[
            {
                "step_id": "s1",
                "kind": "pipeline",
                "pipeline_name": "chembl_activity",
                "status": "success",
                "records_extracted": 42,
            }
        ],
    )
    written = write_workflow_run_report(report, root=tmp_path)
    payload = json.loads(written.json_path.read_text(encoding="utf-8"))
    assert payload["totals"]["records_extracted_sum"] == 42
    assert "Steps" in written.markdown_path.read_text(encoding="utf-8")


def test_latest_pointer_uses_sanitized_identity_owner_with_custom_directory(
    tmp_path: Path,
) -> None:
    report = build_workflow_run_report(
        identity={
            "workflow_name": "unsafe/owner",
            "workflow_run_id": "wf1",
            "status": "success",
        },
        plan_steps=[],
        execution_steps=[],
    )
    custom_directory = tmp_path / "custom" / "artifacts"

    written = write_workflow_run_report(
        report,
        root=tmp_path,
        directory=custom_directory,
    )

    assert written.json_path.parent == custom_directory
    assert (
        written.latest_path == tmp_path / "workflow" / "unsafe_owner" / "_latest.json"
    )
    assert written.latest_path.is_file()


def test_write_json_cleans_temporary_file_when_replace_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "report.json"

    def _fail_replace(_source: Path, _target: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(Path, "replace", _fail_replace)
    try:
        write_json(target, {"schema_version": "pipeline_run_report_v1"})
    except (OSError, Exception) as exc:
        assert "replace failed" in str(exc)
    else:
        raise AssertionError("write_json must surface atomic replacement failures")

    assert not target.exists()
    assert list(tmp_path.glob(".*.tmp")) == []


def test_require_store_raises_without_injection(monkeypatch) -> None:
    monkeypatch.setattr(run_report_writer, "_injected_store", None)
    target = Path("unused.json")
    try:
        run_report_writer.write_json(target, {"ok": True})
    except TypeError as exc:
        assert "RunReportStorePort" in str(exc)
    else:
        raise AssertionError("write_json must require an injected store")


def test_writer_module_does_not_import_infrastructure() -> None:
    source = Path(run_report_writer.__file__).read_text(encoding="utf-8")
    assert "bioetl.infrastructure" not in source


def test_atomic_write_uses_injected_store(tmp_path: Path) -> None:
    written: list[tuple[Path, str]] = []

    class _MemoryStore:
        def mkdir(self, path: Path) -> None:
            path.mkdir(parents=True, exist_ok=True)

        def write_text(self, path: Path, content: str) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written.append((path, content))

        def read_text(self, path: Path) -> str:
            return path.read_text(encoding="utf-8")

    target = tmp_path / "report.md"
    run_report_writer._atomic_write_text(target, "hello\n", store=_MemoryStore())
    assert target.read_text(encoding="utf-8") == "hello\n"
    assert written == [(target, "hello\n")]
