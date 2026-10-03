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
from bioetl.domain.composite.result import CompositeResult, MergeResult, SeedResult
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.infrastructure.time import SystemClock


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["success", "error", "cancel"])
@pytest.mark.parametrize("child_verdict", ["OK", "WARN"])
@pytest.mark.parametrize("dq_verdict", ["OK", "WARN", "ERROR", None])
async def test_parent_records_terminal_evidence(
    tmp_path, outcome, child_verdict, dq_verdict
):
    archive = MagicMock()
    service = CompositeRunReportService(
        "composite_assay",
        "parent-manifest",
        FileRunReportStoreAdapter(),
        tmp_path,
        SystemClock(),
        MagicMock(),
        MagicMock(),
        archive=archive,
    )
    child_path = tmp_path / "child.json"
    child_path.write_text(
        json.dumps(
            {
                "identity": {"run_id": "child-id"},
                "observations": {
                    "Provider": {"verdict": child_verdict},
                    **({"Data Quality": {"verdict": dq_verdict}} if dq_verdict else {}),
                },
            }
        )
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
            merge_result=MergeResult(
                records_merged=9,
                records_from_seed=10,
                output_silver_path="silver/composite",
                output_gold_path="gold/composite",
            ),
        )

    if outcome == "success":
        await service.execute("parent-id", body)
    else:
        with pytest.raises(
            ValueError if outcome == "error" else asyncio.CancelledError
        ):
            await service.execute("parent-id", body)
    report = json.loads(
        (
            tmp_path / "pipeline/composite_assay/parent-id/pipeline-run-report.json"
        ).read_text()
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
    assert report["observations"]["Data Quality"]["verdict"] == (
        dq_verdict or "INCOMPLETE"
    )
    assert report["observations"]["Data Quality"]["facts"]["child_run_ids"] == [
        "child-id"
    ]
    assert (
        report["observations"]["Data Validation"]["reason"] == "actual_merge_validation"
    )
    assert report["io"]["child_runs"][0]["run_id"] == "child-id"
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
            FileRunReportStoreAdapter(),
            tmp_path,
            SystemClock(),
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
            (
                tmp_path
                / f"pipeline/composite_assay/parent-{i}/pipeline-run-report.json"
            ).read_text()
        )
        assert [c["run_id"] for c in report["io"]["child_runs"]] == [f"child-{i}"]
        assert report["observations"]["Provider"]["verdict"] == "INCOMPLETE"
