"""Unit tests for stage accounting and pipeline report builder."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

import json
from pathlib import Path
from typing import cast

from bioetl.domain.ports import StageAccountingPort
from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.domain.run_reports.models import StageId, TrackingCoverage
from bioetl.domain.run_reports.pipeline_builder import build_pipeline_run_report
from bioetl.domain.run_reports.reason_catalog import default_reason_catalog
from bioetl.domain.run_reports.workflow_builder import build_workflow_run_report


def test_conservation_invariant_ok() -> None:
    acc = StageAccountingAccumulator()
    acc.record_in(StageId.SILVER.value, 100)
    acc.record_out(StageId.SILVER.value, 70)
    acc.record_removal(
        StageId.SILVER.value,
        outcome="filtered_out",
        reason_code="structural_policy_required_missing",
        count=20,
    )
    acc.record_removal(
        StageId.SILVER.value,
        outcome="quarantined",
        reason_code="SCHEMA_VALIDATION_FAILURE",
        count=10,
    )
    layers = acc.snapshot_layers_from_metrics(
        {
            "records_bronze": 100,
            "records_silver": 70,
            "records_gold": 0,
            "records_filtered_out": 20,
            "records_quarantined": 10,
        }
    )
    funnel = acc.snapshot_funnel(layers)
    silver = next(row for row in funnel if row.stage_id == "silver")
    assert silver.records_in == silver.records_out + silver.removed_total
    assert silver.unaccounted == 0
    assert silver.balance_status.value == "OK"


def test_unknown_reason_maps_to_catalog_unknown() -> None:
    acc = StageAccountingAccumulator()
    acc.record_removal(
        StageId.SILVER.value,
        outcome="quarantined",
        reason_code="totally_unknown_xyz",
        count=3,
    )
    assert acc.unmapped_reason_count >= 1
    top = acc.top_reasons()
    assert top[0]["reason_code"] == default_reason_catalog().unknown_code
    assert top[0]["count"] == 3


def test_accumulator_satisfies_stage_accounting_port() -> None:
    port = cast(StageAccountingPort, StageAccountingAccumulator())
    port.record_in(StageId.SILVER.value, 2)
    port.record_out(StageId.SILVER.value, 2)
    layers = port.snapshot_layers_from_metrics({"records_bronze": 2})
    assert port.snapshot_funnel(layers)[2].records_in == 2


def test_sample_refs_are_unique_and_bounded() -> None:
    acc = StageAccountingAccumulator()
    for index in range(30):
        acc.record_removal(
            StageId.SILVER.value,
            outcome="quarantined",
            reason_code="SCHEMA_VALIDATION_FAILURE",
            sample_ref=f"id-{index % 25}",
        )
    layers = acc.snapshot_layers_from_metrics({})
    silver = acc.snapshot_funnel(layers)[2]
    samples = silver.removals[0].sample_refs
    assert len(samples) == 20
    assert len(set(samples)) == 20


def test_overcount_is_failing_not_silently_balanced() -> None:
    acc = StageAccountingAccumulator()
    acc.record_in(StageId.SILVER.value, 5)
    acc.record_out(StageId.SILVER.value, 6)
    layers = acc.snapshot_layers_from_metrics({})
    silver = acc.snapshot_funnel(layers)[2]
    assert silver.balance_status.value == "FAILING"


def test_pipeline_report_builder_from_instrumented_accounting() -> None:
    acc = StageAccountingAccumulator()
    acc.record_in(StageId.EXTRACT.value, 1000)
    acc.record_out(StageId.EXTRACT.value, 1000)
    acc.record_in(StageId.BRONZE.value, 1000)
    acc.record_out(StageId.BRONZE.value, 1000)
    acc.record_in(StageId.SILVER.value, 1000)
    acc.record_out(StageId.SILVER.value, 850)
    acc.record_removal(
        StageId.SILVER.value,
        outcome="filtered_out",
        reason_code="structural_policy_required_missing",
        count=80,
    )
    acc.record_removal(
        StageId.SILVER.value,
        outcome="quarantined",
        reason_code="SCHEMA_VALIDATION_FAILURE",
        count=50,
    )
    acc.record_removal(
        StageId.SILVER.value,
        outcome="deduplicated",
        reason_code="DEDUP_KEY_COLLISION",
        count=20,
    )
    acc.record_in(StageId.GOLD.value, 850)
    acc.record_out(StageId.GOLD.value, 820)
    acc.record_removal(
        StageId.GOLD.value,
        outcome="excluded_by_contract",
        reason_code="gold_contract_required_failure",
        count=30,
    )

    report = build_pipeline_run_report(
        identity={
            "run_id": "run-1",
            "pipeline_name": "chembl_activity",
            "run_type": "incremental",
            "status": "success",
        },
        metrics={
            "records_fetched": 1000,
            "records_bronze": 1000,
            "records_silver": 850,
            "records_gold": 820,
            "records_filtered_out": 80,
            "records_quarantined": 50,
            "records_gold_excluded_by_contract": 30,
        },
        accounting=acc,
    )
    payload = report.to_dict()
    assert payload["schema_version"] == "pipeline_run_report_v1"
    assert payload["layers"]["bronze_records"] == 1000
    silver = next(row for row in payload["funnel"] if row["stage_id"] == "silver")
    assert silver["removed_total"] == 150
    assert len(silver["removals"]) == 3
    assert report.tracking_coverage in {
        TrackingCoverage.FULL,
        TrackingCoverage.PARTIAL,
    }


def test_workflow_report_extracted_rollup() -> None:
    report = build_workflow_run_report(
        identity={
            "workflow_name": "demo",
            "status": "success",
            "workflow_run_id": "wf-1",
        },
        plan_steps=[
            {
                "step_id": "seed",
                "kind": "pipeline",
                "pipeline_name": "chembl_activity",
                "depends_on": [],
            },
            {
                "step_id": "dep",
                "kind": "pipeline",
                "pipeline_name": "chembl_assay",
                "depends_on": ["seed"],
            },
        ],
        execution_steps=[
            {
                "step_id": "seed",
                "kind": "pipeline",
                "pipeline_name": "chembl_activity",
                "status": "success",
                "records_extracted": 1000,
                "records_silver": 850,
            },
            {
                "step_id": "dep",
                "kind": "pipeline",
                "pipeline_name": "chembl_assay",
                "status": "success",
                "records_extracted": 200,
                "records_silver": 190,
            },
        ],
    )
    payload = report.to_dict()
    assert payload["schema_version"] == "workflow_run_report_v1"
    assert payload["totals"]["records_extracted_sum"] == 1200
    assert payload["totals"]["steps_succeeded"] == 2
    assert payload["index"]["chembl_activity"]["records_extracted"] == 1000


def test_golden_pipeline_fixture_shape() -> None:
    path = (
        Path(__file__).resolve().parents[3]
        / "fixtures"
        / "reports"
        / "pipeline_run_report_golden.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "pipeline_run_report_v1"
    assert payload["funnel"][2]["stage_id"] == "silver"
    assert payload["funnel"][2]["removed_total"] == 150
