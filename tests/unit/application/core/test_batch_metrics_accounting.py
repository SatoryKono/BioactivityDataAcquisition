"""Unit tests for batch metrics stage-accounting helpers (ARCH-CONT-02)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.core.batch_metrics_accounting import (
    _record_batch_lifecycle_event,
    _record_filtered_out_stage_metrics,
    _record_processed_stage_accounting,
    _record_silver_removal_accounting,
    _record_stage_outcome_accounting,
    _silver_filter_rejection_labels,
)

pytestmark = pytest.mark.unit


def test_record_silver_removal_accounting_noops_without_context() -> None:
    with patch(
        "bioetl.application.core.batch_metrics_accounting.get_stage_accounting",
        return_value=None,
    ):
        _record_silver_removal_accounting(
            outcome="filtered_out",
            reason_code="FILTERED_OUT_SILVER",
            count=1,
        )


def test_record_silver_removal_accounting_records_positive_count() -> None:
    accounting = MagicMock()
    with patch(
        "bioetl.application.core.batch_metrics_accounting.get_stage_accounting",
        return_value=accounting,
    ):
        _record_silver_removal_accounting(
            outcome="quarantined",
            reason_code="SCHEMA_VALIDATION_FAILURE",
            count=3,
        )
    accounting.record_removal.assert_called_once()


def test_record_processed_stage_accounting_stages() -> None:
    accounting = MagicMock()
    with patch(
        "bioetl.application.core.batch_metrics_accounting.get_stage_accounting",
        return_value=accounting,
    ):
        _record_processed_stage_accounting("bronze", 2)
        _record_processed_stage_accounting("silver", 2)
        _record_processed_stage_accounting("gold", 2)
        _record_processed_stage_accounting("quarantined", 1)
        _record_processed_stage_accounting("unknown_stage", 1)
        _record_processed_stage_accounting("bronze", 0)
    assert accounting.record_in.called
    assert accounting.record_out.called
    assert accounting.record_removal.called


def test_record_stage_outcome_accounting_gold_and_silver() -> None:
    accounting = MagicMock()
    with patch(
        "bioetl.application.core.batch_metrics_accounting.get_stage_accounting",
        return_value=accounting,
    ):
        _record_stage_outcome_accounting("gold", "written", 4)
        _record_stage_outcome_accounting("gold", "records", 1)
        _record_stage_outcome_accounting("gold", "quarantined", 1)
        _record_stage_outcome_accounting("silver", "filtered_out", 2)
        _record_stage_outcome_accounting("bronze", "written", 1)
    with patch(
        "bioetl.application.core.batch_metrics_accounting.get_stage_accounting",
        return_value=None,
    ):
        _record_stage_outcome_accounting("gold", "written", 1)
    assert accounting.record_out.called
    assert accounting.record_removal.called


def test_record_filtered_out_stage_metrics_projects_pipeline_metrics() -> None:
    pipeline_metrics = MagicMock()
    with patch(
        "bioetl.application.core.batch_metrics_accounting.get_stage_accounting",
        return_value=None,
    ):
        _record_filtered_out_stage_metrics(
            pipeline_metrics,
            run_type_label="incremental",
            count=5,
        )
    assert pipeline_metrics.record_stage_records.call_count == 2


def test_record_batch_lifecycle_event_forwards() -> None:
    pipeline_metrics = MagicMock()
    _record_batch_lifecycle_event(
        pipeline_metrics,
        run_type_label="incremental",
        event="created",
        stage="bronze",
        status="success",
        record_count=10,
    )
    pipeline_metrics.record_batch_lifecycle_event.assert_called_once()


def test_silver_filter_rejection_labels_variants() -> None:
    assert _silver_filter_rejection_labels(None) == (None, None, None)
    assert _silver_filter_rejection_labels(
        {"reason_code": "R1", "rule_type": "business", "field": "x"}
    ) == ("R1", "business", "x")
    assert _silver_filter_rejection_labels({"policy_stage": "structural"})[1] == (
        "structural_policy"
    )
    assert _silver_filter_rejection_labels({"policy_stage": "other"})[1] is None
