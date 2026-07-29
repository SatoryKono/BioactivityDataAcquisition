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
"""Unit tests for application-level pipeline metrics facade."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder


@pytest.mark.unit
def test_record_quarantine_records_uses_generic_counter() -> None:
    metrics = MagicMock()
    recorder = PipelineMetricsRecorder(metrics, "chembl_activity")

    recorder.record_quarantine_records(reason="FILTERED_OUT_SILVER", count=2)

    metrics.increment_counter.assert_called_once_with(
        "bioetl_quarantine_records_total",
        2,
        {
            "pipeline": "chembl_activity",
            "reason": "FILTERED_OUT_SILVER",
        },
    )


@pytest.mark.unit
def test_record_dq_validation_failures_uses_generic_counter() -> None:
    metrics = MagicMock()
    recorder = PipelineMetricsRecorder(metrics, "chembl_activity")

    recorder.record_dq_validation_failures(stage="threshold", severity="soft_fail")

    metrics.increment_counter.assert_called_once_with(
        "bioetl_dq_validation_failures_total",
        1,
        {
            "pipeline": "chembl_activity",
            "stage": "threshold",
            "severity": "soft_fail",
        },
    )


@pytest.mark.unit
def test_record_silver_filter_rejections_uses_generic_counter() -> None:
    metrics = MagicMock()
    recorder = PipelineMetricsRecorder(metrics, "chembl_activity")

    recorder.record_silver_filter_rejections(
        run_type="incremental",
        reason_code="required_field_missing",
        rule_type="required_fields",
        field="publication_year",
        count=3,
    )

    metrics.increment_counter.assert_called_once_with(
        "bioetl_silver_filter_rejections_total",
        3,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "reason_code": "required_field_missing",
            "rule_type": "required_fields",
            "field": "publication_year",
        },
    )


@pytest.mark.unit
def test_record_record_flow_uses_generic_counter() -> None:
    metrics = MagicMock()
    recorder = PipelineMetricsRecorder(metrics, "chembl_activity")

    recorder.record_record_flow(
        run_type="incremental",
        flow_stage="bronze",
        count=4,
    )

    metrics.increment_counter.assert_called_once_with(
        "bioetl_record_flow_records_total",
        4,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "flow_stage": "bronze",
        },
    )


@pytest.mark.unit
def test_record_stage_records_uses_generic_counter() -> None:
    metrics = MagicMock()
    recorder = PipelineMetricsRecorder(metrics, "chembl_activity")

    recorder.record_stage_records(
        run_type="incremental",
        stage="validation",
        outcome="evaluated",
        count=9,
    )

    metrics.increment_counter.assert_called_once_with(
        "bioetl_stage_records_total",
        9,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "stage": "validation",
            "outcome": "evaluated",
        },
    )


@pytest.mark.unit
def test_record_stage_records_allows_zero_for_series_initialization() -> None:
    metrics = MagicMock()
    recorder = PipelineMetricsRecorder(metrics, "chembl_activity")

    recorder.record_stage_records(
        run_type="incremental",
        stage="silver",
        outcome="valid",
        count=0,
    )

    metrics.increment_counter.assert_called_once_with(
        "bioetl_stage_records_total",
        0,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "stage": "silver",
            "outcome": "valid",
        },
    )


@pytest.mark.unit
def test_initialize_record_accounting_outcomes_creates_all_expected_zero_series() -> (
    None
):
    metrics = MagicMock()
    recorder = PipelineMetricsRecorder(metrics, "chembl_activity")

    recorder.initialize_record_accounting_outcomes(run_type="incremental")

    expected = [
        ("bronze", "records"),
        ("silver", "valid"),
        ("silver", "quarantined"),
        ("silver", "skipped"),
        ("silver", "filtered_out"),
        ("silver", "deduplicated"),
        ("gold", "written"),
        ("gold", "quarantined"),
        ("gold", "skipped"),
        ("gold", "excluded_by_contract"),
        ("gold", "deduplicated"),
    ]
    assert metrics.increment_counter.call_count == len(expected)
    for stage, outcome in expected:
        metrics.increment_counter.assert_any_call(
            "bioetl_stage_records_total",
            0,
            {
                "pipeline": "chembl_activity",
                "run_type": "incremental",
                "stage": stage,
                "outcome": outcome,
            },
        )


@pytest.mark.unit
def test_record_flow_invariant_uses_generic_counter() -> None:
    metrics = MagicMock()
    recorder = PipelineMetricsRecorder(metrics, "chembl_activity")

    recorder.record_flow_invariant(
        run_type="incremental",
        invariant="bronze_partitioned",
        status="passed",
    )

    metrics.increment_counter.assert_called_once_with(
        "bioetl_record_flow_invariants_total",
        1,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "invariant": "bronze_partitioned",
            "status": "passed",
        },
    )


@pytest.mark.unit
def test_record_stage_backlog_uses_generic_gauge() -> None:
    metrics = MagicMock()
    recorder = PipelineMetricsRecorder(metrics, "chembl_activity")

    recorder.record_stage_backlog(
        run_type="incremental",
        stage="output",
        count=3,
    )

    metrics.set_gauge.assert_called_once_with(
        "bioetl_stage_backlog_records",
        3.0,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "stage": "output",
        },
    )


@pytest.mark.unit
def test_record_stage_lag_seconds_uses_generic_gauge() -> None:
    metrics = MagicMock()
    recorder = PipelineMetricsRecorder(metrics, "chembl_activity")

    recorder.record_stage_lag_seconds(
        run_type="incremental",
        stage="validation",
        seconds=12.5,
    )

    metrics.set_gauge.assert_called_once_with(
        "bioetl_stage_lag_seconds",
        12.5,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "stage": "validation",
        },
    )


@pytest.mark.unit
def test_record_dq_disposition_uses_generic_counter() -> None:
    metrics = MagicMock()
    recorder = PipelineMetricsRecorder(metrics, "chembl_activity")

    recorder.record_dq_disposition(
        stage="validation",
        disposition="warn",
        terminal_status="success",
    )

    metrics.increment_counter.assert_called_once_with(
        "bioetl_dq_dispositions_total",
        1,
        {
            "pipeline": "chembl_activity",
            "stage": "validation",
            "disposition": "warn",
            "terminal_status": "success",
        },
    )


@pytest.mark.unit
def test_noop_when_metrics_missing() -> None:
    recorder = PipelineMetricsRecorder(None, "chembl_activity")

    recorder.record_quarantine_records(reason="any")
    recorder.record_dq_validation_failures(stage="threshold", severity="hard_fail")
    recorder.record_silver_filter_rejections(run_type="incremental")
    recorder.record_record_flow(run_type="incremental", flow_stage="fetched")
    recorder.record_stage_records(
        run_type="incremental",
        stage="input",
        outcome="fetched",
    )
    recorder.record_flow_invariant(
        run_type="incremental",
        invariant="fetched_equals_bronze",
        status="unknown",
    )
    recorder.record_stage_backlog(
        run_type="incremental",
        stage="ingestion",
        count=0,
    )
    recorder.record_stage_lag_seconds(
        run_type="incremental",
        stage="output",
        seconds=0.0,
    )
    recorder.record_dq_disposition(
        stage="validation",
        disposition="pass",
        terminal_status="success",
    )
