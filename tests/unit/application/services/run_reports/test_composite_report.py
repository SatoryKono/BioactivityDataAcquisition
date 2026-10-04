"""Parent reports preserve their own identity, outcome and child evidence."""

import asyncio
import json
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.run_reports.composite import (
    CompositeRunReportService,
    record_composite_child,
)
from bioetl.application.services.run_reports.observations import record_run_observation
from bioetl.application.services.run_reports.artifact_digest import (
    canonical_report_sha256,
)
from bioetl.domain.composite.result import CompositeResult, MergeResult, SeedResult
from tests.helpers.clock import fixed_test_clock
from tests.helpers.run_report_store import MemoryReportStore


pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize("damage", ["wrong_identity", "invalid_json", "missing_file"])
async def test_damaged_child_report_cannot_produce_success_message(tmp_path, damage):
    child_path = tmp_path / "child.json"
    store = MemoryReportStore()
    if damage == "wrong_identity":
        store.write_text(
            str(child_path), json.dumps({"identity": {"run_id": "other-run"}})
        )
    elif damage == "invalid_json":
        store.write_text(str(child_path), "{broken")
    service = CompositeRunReportService(
        "composite_assay",
        "manifest",
        store,
        tmp_path,
        fixed_test_clock(),
        MagicMock(),
        MagicMock(),
    )

    async def body():
        record_composite_child(
            RunResult(
                status=PipelineRunResult.SUCCESS,
                pipeline_name="chembl_assay",
                run_id="child-id",
                run_type="incremental",
                run_report_json_path=str(child_path),
            )
        )
        return CompositeResult(
            "composite_assay",
            "parent-id",
            SeedResult("chembl_assay", records_silver=1),
            merge_result=MergeResult(records_merged=1, output_silver_path="silver"),
        )

    result = await service.execute("parent-id", body)
    assert result.had_warnings is True
    assert result.provider_warnings == ("chembl_assay",)
    from bioetl.interfaces.cli.commands.domains.composite.execution import (
        build_run_composite_result,
    )

    successful, message = build_run_composite_result(result)
    assert successful is True
    assert "Provider warnings: chembl_assay" in message
    report = json.loads(
        next(
            value
            for path, value in store.files.items()
            if path.endswith("pipeline-run-report.json")
        )
    )
    assert report["observations"]["Provider"]["verdict"] == "INCOMPLETE"
    assert report["observations"]["Data Quality"]["verdict"] == "INCOMPLETE"
    assert report["identity"]["completion_status"] == "completed_with_warnings"


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["success", "error", "cancel"])
@pytest.mark.parametrize("child_verdict", ["OK", "WARN", "ERROR", "UNKNOWN"])
@pytest.mark.parametrize("dq_verdict", ["OK", "WARN", "ERROR", "UNKNOWN", None])
@pytest.mark.parametrize("warnings", [False, True])
async def test_parent_records_terminal_evidence(
    tmp_path, outcome, child_verdict, dq_verdict, warnings
):
    archive = MagicMock()
    service = CompositeRunReportService(
        "composite_assay",
        "parent-manifest",
        MemoryReportStore(),
        tmp_path,
        fixed_test_clock(),
        MagicMock(),
        MagicMock(),
        archive=archive,
    )
    child_path = tmp_path / "child.json"
    service.store.write_text(
        str(child_path),
        json.dumps(
            {
                "identity": {"run_id": "child-id"},
                "observations": {
                    "Provider": {"verdict": child_verdict},
                    **({"Data Quality": {"verdict": dq_verdict}} if dq_verdict else {}),
                },
            }
        ),
    )

    async def body():
        # Archive trust is finalized after the initial report is persisted.
        # Its provisional state must not become a permanent execution warning.
        record_run_observation(
            "Control Plane", verdict="INCOMPLETE", reason="archive_pending", facts={}
        )
        record_composite_child(
            RunResult(
                status=PipelineRunResult.SUCCESS,
                pipeline_name="chembl_assay",
                run_id="child-id",
                run_type="incremental",
                run_report_json_path=str(child_path),
            )
        )
        record_run_observation(
            "Data Validation", verdict="OK", reason="actual_merge_validation", facts={}
        )
        if outcome == "error":
            raise ValueError("merge write failed")
        if outcome == "cancel":
            raise asyncio.CancelledError()
        return CompositeResult(
            "composite_assay",
            "parent-id",
            SeedResult("chembl_assay", records_silver=10),
            had_warnings=warnings,
            merge_result=MergeResult(
                records_merged=9,
                records_from_seed=10,
                output_silver_path="silver/composite",
                output_gold_path="gold/composite",
            ),
        )

    if outcome == "success":
        assessed = await service.execute("parent-id", body)
        expected_warnings = warnings or child_verdict != "OK" or dq_verdict != "OK"
        assert assessed.had_warnings is expected_warnings
        assert assessed.provider_warnings == (
            ("chembl_assay",) if child_verdict != "OK" else ()
        )
        from bioetl.interfaces.cli.commands.domains.composite.execution import (
            build_run_composite_result,
        )

        cli_success, cli_message = build_run_composite_result(assessed)
        assert cli_success is True
        assert bool(cli_message) is expected_warnings
    else:
        with pytest.raises(
            ValueError if outcome == "error" else asyncio.CancelledError
        ):
            await service.execute("parent-id", body)
    report = json.loads(
        service.store.read_text(
            str(
                tmp_path / "pipeline/composite_assay/parent-id/pipeline-run-report.json"
            )
        )
    )
    if outcome == "success":
        archive.assert_called_once()
        archived_result = archive.call_args.args[0]
        assert archived_result.run_id == "parent-id"
        assert archived_result.manifest_id == "parent-manifest"
        assert archived_result.records_gold == 9
        assert (
            json.loads(service.store.read_text(archived_result.run_report_json_path))[
                "identity"
            ]["run_id"]
            == "parent-id"
        )
    else:
        archive.assert_not_called()
    assert report["identity"]["run_id"] == "parent-id"
    assert report["identity"]["manifest_id"] == "parent-manifest"
    assert (
        report["identity"]["status"]
        == {"success": "success", "error": "failed", "cancel": "shutdown"}[outcome]
    )
    assert report["observations"]["Provider"]["verdict"] == child_verdict
    assert report["observations"]["Control Plane"]["verdict"] == "INCOMPLETE"
    expected_dq = dq_verdict or "INCOMPLETE"
    if warnings and outcome == "success" and expected_dq in {"OK", "WARN"}:
        expected_dq = "WARN"
    assert report["observations"]["Data Quality"]["verdict"] == expected_dq
    assert report["identity"]["completion_status"] == (
        "completed_with_warnings"
        if outcome == "success"
        and (warnings or child_verdict != "OK" or dq_verdict != "OK")
        else report["identity"]["status"]
    )
    assert report["observations"]["Data Quality"]["facts"]["child_run_ids"] == [
        "child-id"
    ]
    assert (
        report["observations"]["Data Validation"]["reason"] == "actual_merge_validation"
    )
    assert report["io"]["child_runs"][0]["run_id"] == "child-id"
    child_artifact = next(
        item
        for item in report["artifacts"]
        if item["kind"] == "composite_child_run_report"
    )
    assert "\\" not in child_artifact["ref"]
    assert child_artifact["sha256"] == canonical_report_sha256(
        json.loads(service.store.read_text(str(child_path)))
    )
    assert report["layers"]["bronze_records"] == 0
    assert report["layers"]["gold_written"] == (9 if outcome == "success" else 0)
    if outcome != "success":
        assert report["failure"]["error_type"] == (
            "ValueError" if outcome == "error" else "CancelledError"
        )


@pytest.mark.asyncio
async def test_child_scopes_do_not_leak_between_concurrent_parents(tmp_path):
    services = [
        CompositeRunReportService(
            "composite_assay",
            None,
            MemoryReportStore(),
            tmp_path,
            fixed_test_clock(),
            MagicMock(),
            MagicMock(),
        )
        for _ in range(2)
    ]

    async def body(index):
        record_composite_child(
            RunResult(
                PipelineRunResult.FAILED,
                "chembl_assay",
                f"child-{index}",
                "incremental",
            )
        )
        await asyncio.sleep(0)
        raise ValueError("test failure")

    await asyncio.gather(
        *(
            service.execute(f"parent-{i}", lambda i=i: body(i))
            for i, service in enumerate(services)
        ),
        return_exceptions=True,
    )
    for i in range(2):
        report = json.loads(
            services[i].store.read_text(
                str(
                    tmp_path
                    / f"pipeline/composite_assay/parent-{i}/pipeline-run-report.json"
                )
            )
        )
        assert [c["run_id"] for c in report["io"]["child_runs"]] == [f"child-{i}"]
        assert report["observations"]["Provider"]["verdict"] == "INCOMPLETE"
