# pyright: reportArgumentType=false

"""Focused tests for CR-FULL 20260816 run-report accounting residuals (#8889)."""

from __future__ import annotations

from types import SimpleNamespace

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
from bioetl.domain.run_reports.workflow_reasons import (
    _as_int,
    _optional_reason_text,
    build_reasons_rollup,
    normalize_top_reasons,
)

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


def test_error_type_quarantine_codes_stay_mapped() -> None:
    """DQ ErrorType values must not collapse to UNKNOWN_REASON."""
    for code in (
        "SCHEMA_VIOLATION",
        "INVALID_DATA",
        "MISSING_REQUIRED_FIELD",
        "DATA_QUALITY",
    ):
        assert normalize_reason_code(code) == code
    assert normalize_reason_code(None) == UNKNOWN_REASON
    assert normalize_reason_code("") == UNKNOWN_REASON
    assert normalize_reason_code("not-a-catalog-code") == UNKNOWN_REASON


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


@pytest.mark.parametrize("raw", [None, 1, "reason", b"reason"])
def test_top_reasons_rejects_non_reason_sequences(raw: object) -> None:
    assert normalize_top_reasons(raw) == ()


def test_top_reasons_filters_invalid_entries_and_normalizes_payload() -> None:
    ranked = normalize_top_reasons(
        [
            "invalid",
            {},
            {"reason_code": ""},
            {
                "reason_code": 42,
                "outcome": "filtered_out",
                "reason_family": "quality",
                "count": "3",
            },
        ]
    )
    assert ranked == (
        {
            "reason_code": "42",
            "outcome": "filtered_out",
            "reason_family": "quality",
            "count": 3,
        },
    )


def test_build_reasons_rollup_aggregates_same_semantic_key() -> None:
    rows = [
        SimpleNamespace(
            top_reasons=(
                {
                    "reason_code": "FILTERED",
                    "outcome": "filtered_out",
                    "reason_family": "quality",
                    "count": 2,
                },
            )
        ),
        SimpleNamespace(
            top_reasons=(
                {
                    "reason_code": "FILTERED",
                    "outcome": "filtered_out",
                    "reason_family": "quality",
                    "count": 3,
                },
                {"reason_code": "OTHER", "outcome": 123, "count": 1},
            )
        ),
    ]
    assert build_reasons_rollup(rows) == (
        {
            "reason_code": "FILTERED",
            "outcome": "filtered_out",
            "reason_family": "quality",
            "count": 5,
        },
        {
            "reason_code": "OTHER",
            "outcome": None,
            "reason_family": None,
            "count": 1,
        },
    )


def test_reason_scalar_normalizers_fail_closed() -> None:
    assert _optional_reason_text("kept") == "kept"
    assert _optional_reason_text(1) is None
    assert _as_int(None, default=7) == 7
    assert _as_int(object(), default=8) == 8
    assert _as_int("bad", default=9) == 9
    assert _as_int(float("inf"), default=10) == 10
