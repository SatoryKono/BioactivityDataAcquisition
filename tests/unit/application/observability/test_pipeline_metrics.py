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
    recorder.record_dq_disposition(
        stage="validation",
        disposition="pass",
        terminal_status="success",
    )
