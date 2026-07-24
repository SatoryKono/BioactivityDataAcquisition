"""Unit tests for run report query helpers."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from pathlib import Path

from bioetl.application.services.run_reports.query import (
    diff_pipeline_reports,
    list_pipeline_reports,
    load_pipeline_report,
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
