"""Backend-independent run-report storage contract."""

from pathlib import Path
import pytest
from tests.helpers.run_report_store import MemoryReportStore
from bioetl.application.services.run_reports.query import (
    list_pipeline_reports,
    load_pipeline_report,
    prune_reports,
)
from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.domain.run_reports.pipeline_builder import build_pipeline_run_report

pytestmark = pytest.mark.unit


def test_injected_stores_isolate_write_read_list_and_prune() -> None:
    first, second = MemoryReportStore(), MemoryReportStore()
    root = Path("virtual-reports")
    for store, run_ids in ((first, ("old", "new")), (second, ("other",))):
        for run_id in run_ids:
            report = build_pipeline_run_report(
                identity={
                    "pipeline_name": "chembl_activity",
                    "run_id": run_id,
                    "status": "success",
                },
                metrics={},
            )
            write_pipeline_run_report(report, root=root, store=store)
    assert (
        load_pipeline_report(
            pipeline_name="chembl_activity", latest=True, root=root, store=first
        )["identity"]["run_id"]
        == "new"
    )
    assert (
        load_pipeline_report(
            pipeline_name="chembl_activity", run_id="other", root=root, store=first
        )
        is None
    )
    assert [r.run_id for r in list_pipeline_reports(root=root, store=first)] == [
        "new",
        "old",
    ]
    candidates = prune_reports(kind="pipeline", max_count=1, root=root, store=first)
    assert candidates == [(root / "pipeline" / "chembl_activity" / "old").as_posix()]
    assert len(list_pipeline_reports(root=root, store=first)) == 2
    assert (
        prune_reports(
            kind="pipeline", max_count=1, root=root, dry_run=False, store=first
        )
        == candidates
    )
    assert [r.run_id for r in list_pipeline_reports(root=root, store=first)] == ["new"]
    assert [r.run_id for r in list_pipeline_reports(root=root, store=second)] == [
        "other"
    ]
