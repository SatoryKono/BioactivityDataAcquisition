# pyright: reportArgumentType=false

"""Focused tests for CR-FULL 20260816 run-report accounting residuals (#8889)."""

from __future__ import annotations

import pytest

from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.domain.run_reports.models import StageId
from bioetl.domain.run_reports.reason_catalog import (
    ReasonCatalog,
    ReasonCatalogEntry,
    UNKNOWN_REASON,
    normalize_reason_code,
)
from bioetl.domain.run_reports.workflow_builder import build_workflow_run_report
from bioetl.domain.run_reports.workflow_reasons import normalize_top_reasons

pytestmark = pytest.mark.unit


def test_mapped_zero_is_not_replaced_by_coarse_metric() -> None:
    acc = StageAccountingAccumulator()
    acc.mark_instrumented(StageId.SILVER.value)
    layers = acc.snapshot_layers_from_metrics(
        {
            "records_bronze": 10,
            "records_silver": 10,
            "records_filtered_out": 7,
            "records_quarantined": 3,
        }
    )
    assert layers.silver_filtered_out == 0
    assert layers.silver_quarantined == 0


def test_coarse_metrics_used_when_mapping_is_unavailable() -> None:
    acc = StageAccountingAccumulator()
    layers = acc.snapshot_layers_from_metrics(
        {
            "records_bronze": 10,
            "records_silver": 3,
            "records_filtered_out": 7,
        }
    )
    assert layers.silver_filtered_out == 7


def test_custom_catalog_does_not_accept_omitted_builtin_codes() -> None:
    catalog = ReasonCatalog(
        version="custom_v1",
        entries={
            "CUSTOM_ONLY": ReasonCatalogEntry(
                code="CUSTOM_ONLY",
                family="structural",
                default_outcome="filtered_out",
                layer="silver",
            ),
            UNKNOWN_REASON: ReasonCatalogEntry(
                code=UNKNOWN_REASON,
                family="system",
                default_outcome="other",
                layer="silver",
            ),
        },
        unknown_code=UNKNOWN_REASON,
    )
    assert normalize_reason_code("CUSTOM_ONLY", catalog) == "CUSTOM_ONLY"
    assert normalize_reason_code("FILTERED_OUT_SILVER", catalog) == UNKNOWN_REASON


def test_measured_zero_extracted_is_not_replaced_by_payload() -> None:
    report = build_workflow_run_report(
        identity={"workflow_id": "wf"},
        plan_steps=(),
        execution_steps=[
            {
                "step_id": "s1",
                "status": "success",
                "records_extracted": 0,
                "payload": {"records_extracted": 9, "records_bronze": 9},
            }
        ],
    )
    assert report.execution[0].records_extracted == 0


def test_top_reasons_are_largest_by_count_regardless_of_input_order() -> None:
    raw = (
        {"reason_code": "A", "count": 1},
        {"reason_code": "B", "count": 5},
        {"reason_code": "C", "count": 3},
        {"reason_code": "D", "count": 4},
    )
    ranked = normalize_top_reasons(raw)
    assert [item["reason_code"] for item in ranked] == ["B", "D", "C"]
    reversed_ranked = normalize_top_reasons(tuple(reversed(raw)))
    assert [item["reason_code"] for item in reversed_ranked] == ["B", "D", "C"]
