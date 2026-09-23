# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict.
"""Unit tests for nested/composite pipeline-run-report persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.execution.nested_run_report import (
    ReportingExecutionRunner,
    composite_run_report_pipeline_name,
    extract_runner_metrics,
    maybe_wrap_reporting_runner,
    persist_composite_pipeline_run_report,
    persist_nested_pipeline_run_report,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    RunOptions,
)
from bioetl.domain.composite.result import CompositeResult, MergeResult, SeedResult
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from tests.helpers.clock import FixedClock

_STARTED = datetime(2026, 9, 23, 13, 0, 41, tzinfo=UTC)
_COMPLETED = datetime(2026, 9, 23, 13, 1, 11, tzinfo=UTC)


class _StubRunner:
    def __init__(self, *, fail: bool = False) -> None:
        self.run_id = "0e2abe3d-2b3b-5888-9d34-304db13cd007"
        self.manifest_id = "373fb0dd-fc00-5f7d-a784-d8543d8d485e"
        self.shutdown_signal = None
        self.debug_export_uri = None
        self.debug_export_hash = None
        self.logger = MagicMock()
        self._fail = fail
        self._metrics = {
            "records_fetched": 26,
            "records_bronze": 26,
            "records_silver": 26,
            "records_gold": 0,
            "records_gold_excluded_by_contract": 0,
            "records_quarantined": 0,
            "records_filtered_out": 0,
        }

    @property
    def execution_metrics(self) -> dict[str, int]:
        return self._metrics

    async def run(self) -> None:
        if self._fail:
            raise RuntimeError("enricher boom")


@pytest.mark.unit
def test_extract_runner_metrics_defaults_missing_keys() -> None:
    runner = MagicMock()
    runner.execution_metrics = {"records_fetched": 2, "records_silver": "3"}
    metrics = extract_runner_metrics(runner)
    assert metrics["records_fetched"] == 2
    assert metrics["records_silver"] == 3
    assert metrics["records_gold"] == 0
    assert metrics["records_quarantined"] == 0


@pytest.mark.unit
def test_persist_nested_enricher_report_writes_json_and_md(tmp_path: Path) -> None:
    written = persist_nested_pipeline_run_report(
        runner=_StubRunner(),
        pipeline_name="pubmed_publication",
        options=RunOptions(
            run_type="incremental",
            skip_gold=True,
            execution_context="enricher",
            limit=26,
        ),
        started_at=_STARTED,
        completed_at=_COMPLETED,
        store=FileRunReportStoreAdapter(),
        report_root=tmp_path,
    )
    assert written.run_report_error is None
    json_path = (
        tmp_path
        / "pipeline"
        / "pubmed_publication"
        / _StubRunner().run_id
        / ("pipeline-run-report.json")
    )
    md_path = json_path.with_suffix(".md")
    assert json_path.is_file()
    assert md_path.is_file()
    payload = json_path.read_text(encoding="utf-8")
    assert '"pipeline_name": "pubmed_publication"' in payload
    assert '"execution_context"' not in payload or "enricher" in payload
    assert written.run_report_json_path == str(json_path)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reporting_runner_writes_report_on_success(tmp_path: Path) -> None:
    inner = _StubRunner()
    wrapper = ReportingExecutionRunner(
        inner=inner,
        pipeline_name="pubmed_publication",
        options=RunOptions(run_type="incremental", execution_context="enricher"),
        store=FileRunReportStoreAdapter(),
        report_root=tmp_path,
        clock=FixedClock(_STARTED),
    )
    await wrapper.run()
    report = (
        tmp_path
        / "pipeline"
        / "pubmed_publication"
        / inner.run_id
        / "pipeline-run-report.json"
    )
    assert report.is_file()
    assert '"status": "success"' in report.read_text(encoding="utf-8")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reporting_runner_writes_failed_report_then_reraises(
    tmp_path: Path,
) -> None:
    inner = _StubRunner(fail=True)
    wrapper = ReportingExecutionRunner(
        inner=inner,
        pipeline_name="pubmed_publication",
        options=RunOptions(run_type="incremental", execution_context="enricher"),
        store=FileRunReportStoreAdapter(),
        report_root=tmp_path,
        clock=FixedClock(_STARTED),
    )
    with pytest.raises(RuntimeError, match="enricher boom"):
        await wrapper.run()
    report = (
        tmp_path
        / "pipeline"
        / "pubmed_publication"
        / inner.run_id
        / "pipeline-run-report.json"
    )
    assert report.is_file()
    text = report.read_text(encoding="utf-8")
    assert '"status": "failed"' in text
    assert "RuntimeError" in text


@pytest.mark.unit
def test_maybe_wrap_skips_non_pipeline_runner() -> None:
    runner = {"kind": "double"}
    wrapped = maybe_wrap_reporting_runner(
        runner,
        pipeline_name="pubmed_publication",
        options=RunOptions(),
        store=FileRunReportStoreAdapter(),
    )
    assert wrapped is runner


@pytest.mark.unit
def test_maybe_wrap_skips_when_options_are_not_run_options() -> None:
    runner = MagicMock()
    wrapped = maybe_wrap_reporting_runner(
        runner,
        pipeline_name="pubmed_publication",
        options={"run_type": "incremental"},
        store=FileRunReportStoreAdapter(),
    )
    assert wrapped is runner


@pytest.mark.unit
def test_persist_composite_helper_skips_when_store_missing() -> None:
    from types import SimpleNamespace

    from bioetl.application.composite.runner_pkg.runner_lifecycle_flow import (
        _persist_composite_run_report,
    )

    _persist_composite_run_report(
        SimpleNamespace(
            _run_report_store=None, _runtime=SimpleNamespace(dry_run=False)
        ),
        MagicMock(),
    )


@pytest.mark.unit
def test_persist_composite_parent_report(tmp_path: Path) -> None:
    result = CompositeResult(
        composite_name="publication",
        composite_run_id="0655a6f6-e3e4-57e6-8bc7-554c06dc0054",
        seed_result=SeedResult(
            pipeline_name="chembl_publication",
            records_extracted=10,
            records_silver=10,
        ),
        merge_result=MergeResult(records_merged=10, records_from_seed=10),
        started_at=_STARTED,
        completed_at=_COMPLETED,
    )
    written = persist_composite_pipeline_run_report(
        result=result,
        store=FileRunReportStoreAdapter(),
        options=RunOptions(run_type="incremental", execution_context="composite"),
        report_root=tmp_path,
        manifest_id="manifest-1",
    )
    assert written.run_report_error is None
    pipeline = composite_run_report_pipeline_name("publication")
    assert pipeline == "composite_publication"
    report = (
        tmp_path
        / "pipeline"
        / pipeline
        / result.composite_run_id
        / "pipeline-run-report.json"
    )
    assert report.is_file()
    text = report.read_text(encoding="utf-8")
    assert '"pipeline_name": "composite_publication"' in text
    assert '"status": "success"' in text
