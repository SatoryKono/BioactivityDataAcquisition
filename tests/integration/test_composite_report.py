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
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.infrastructure.time import SystemClock

pytestmark = pytest.mark.integration


def test_child_report_artifact_stays_inside_parent_and_detects_tampering(tmp_path):
    from bioetl.application.services.run_reports.composite_evidence import (
        snapshot_child_reports,
    )
    from bioetl.interfaces.http._selected_run_artifact_probes import _artifact_probes

    from dataclasses import replace
    from bioetl.domain.run_reports.pipeline_builder import build_pipeline_run_report
    from bioetl.domain.run_reports.selected_status import DOMAINS
    from bioetl.application.services.run_reports.writer import write_pipeline_run_report

    draft = build_pipeline_run_report(
        identity={
            "run_id": "child",
            "pipeline_name": "chembl_assay",
            "status": "success",
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:01:00+00:00",
        },
        metrics={},
    )
    draft = replace(
        draft,
        observations={
            name: {"verdict": "OK", "reason": "checked", "facts": {"count": 0}}
            for name in DOMAINS[1:]
        },
    )
    source = write_pipeline_run_report(
        draft, root=tmp_path / "source", store=FileRunReportStoreAdapter()
    ).json_path
    child = RunResult(
        status=PipelineRunResult.SUCCESS,
        pipeline_name="chembl_assay",
        run_id="child",
        run_type="incremental",
        run_report_json_path=str(source),
    )
    parent = tmp_path / "parent"
    store = FileRunReportStoreAdapter()
    artifacts = snapshot_child_reports([child], parent, store)
    probes, _ = _artifact_probes({"artifacts": list(artifacts)}, parent)
    assert probes[0]["result"] == "pass"
    saved = parent / artifacts[0]["ref"]
    assert saved.resolve().is_relative_to(parent.resolve())
    saved.write_text("tampered")
    probes, _ = _artifact_probes({"artifacts": list(artifacts)}, parent)
    assert probes[0]["reason"] == "child_digest_mismatch"
    with pytest.raises(ValueError, match="differs"):
        snapshot_child_reports([child], parent, store)


def test_child_report_identity_mismatch_fails_closed(tmp_path):
    from bioetl.application.services.run_reports.composite_evidence import (
        snapshot_child_reports,
    )

    source = tmp_path / "child.json"
    source.write_text(
        json.dumps({"identity": {"run_id": "foreign", "pipeline_name": "chembl_assay"}})
    )
    child = RunResult(
        status=PipelineRunResult.SUCCESS,
        pipeline_name="chembl_assay",
        run_id="child",
        run_type="incremental",
        run_report_json_path=str(source),
    )
    with pytest.raises(ValueError, match="identity"):
        snapshot_child_reports(
            [child], tmp_path / "parent", FileRunReportStoreAdapter()
        )


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["success", "error", "cancel"])
@pytest.mark.parametrize("child_verdict", ["OK", "WARN"])
@pytest.mark.parametrize("dq_verdict", ["OK", "WARN", "ERROR", None])
@pytest.mark.parametrize("warnings", [False, True])
async def test_parent_records_terminal_evidence(
    tmp_path, outcome, child_verdict, dq_verdict, warnings
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
                "identity": {"run_id": "child-id", "pipeline_name": "chembl_assay"},
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
            had_warnings=warnings,
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
    from bioetl.interfaces.http._selected_run_artifact_probes import _artifact_probes

    probes, _ = _artifact_probes(
        report, tmp_path / "pipeline/composite_assay/parent-id"
    )
    # These deliberately minimal child fixtures have no schema or frozen revision.
    # Their bytes are retained, but they must not establish strict replay readiness.
    child_probes = [
        probe for probe in probes if str(probe["code"]).startswith("child_report_")
    ]
    assert child_probes and all(
        probe["reason"] == "child_evidence_invalid" for probe in child_probes
    )
    assert all(
        probe["result"] == "pass" for probe in probes if probe not in child_probes
    )
    import hashlib

    for artifact in report["artifacts"]:
        if artifact["kind"] == "composite_child_run_report":
            captured = tmp_path / "pipeline/composite_assay/parent-id" / artifact["ref"]
            assert captured.read_bytes() == child_path.read_bytes()
            assert (
                hashlib.sha256(captured.read_bytes()).hexdigest() == artifact["sha256"]
            )

    assert report["identity"]["manifest_id"] == "parent-manifest"
    assert (
        report["identity"]["status"]
        == {"success": "success", "error": "failed", "cancel": "shutdown"}[outcome]
    )
    assert report["observations"]["Provider"]["verdict"] == child_verdict
    expected_dq = dq_verdict or "INCOMPLETE"
    if warnings and outcome == "success" and expected_dq in {"OK", "WARN"}:
        expected_dq = "WARN"
    assert report["observations"]["Data Quality"]["verdict"] == expected_dq
    assert report["identity"]["completion_status"] == (
        "completed_with_warnings"
        if warnings and outcome == "success"
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
    assert child_artifact["canonical_sha256"] == canonical_report_sha256(
        json.loads(child_path.read_text())
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


@pytest.mark.asyncio
async def test_missing_child_evidence_preserves_original_failure(tmp_path):
    service = CompositeRunReportService(
        "composite_assay",
        "parent-manifest",
        FileRunReportStoreAdapter(),
        tmp_path,
        SystemClock(),
        MagicMock(),
        MagicMock(),
    )

    async def body():
        record_composite_child(
            RunResult(
                status=PipelineRunResult.FAILED,
                pipeline_name="chembl_assay",
                run_id="child-id",
                run_type="incremental",
                run_report_json_path=str(tmp_path / "missing.json"),
            )
        )
        raise ValueError("original provider failure")

    with pytest.raises(ValueError, match="original provider failure"):
        await service.execute("parent-id", body)
    report = json.loads(
        (
            tmp_path / "pipeline/composite_assay/parent-id/pipeline-run-report.json"
        ).read_text()
    )
    assert report["failure"]["error_message"] == "original provider failure"
    assert report["observations"]["Control Plane"]["verdict"] == "INCOMPLETE"
    assert (
        report["observations"]["Control Plane"]["reason"]
        == "child_report_capture_failed"
    )
    assert report["artifacts"][0]["run_id"] == "child-id"
