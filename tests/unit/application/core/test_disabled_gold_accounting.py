"""Skipping Gold is an operator decision, never an unreasoned contract reject."""

import pytest

from types import SimpleNamespace
from unittest.mock import MagicMock

from bioetl.application.core.batch_transformer_attempt_success import _build_gold_record
from bioetl.application.services.execution._pipeline_runner_support import (
    _seed_gold_removals_from_metrics,
)
from bioetl.composition.factories.services.pipeline_batch_executor_builder import (
    _resolve_gold_filter,
)
from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.domain.run_reports.context import (
    bind_stage_accounting,
    reset_stage_accounting,
)
from bioetl.domain.run_reports.pipeline_builder import build_pipeline_run_report


pytestmark = pytest.mark.unit


def test_disabled_gold_has_balanced_skipped_accounting():
    pipeline = SimpleNamespace(
        runtime=SimpleNamespace(skip_gold=True),
        services=SimpleNamespace(metrics=MagicMock()),
        config=SimpleNamespace(
            pipeline_name="chembl_assay", effective_gold_table="chembl.assay"
        ),
    )
    original_filter = MagicMock()
    callback = _resolve_gold_filter(
        pipeline=pipeline, callbacks=SimpleNamespace(gold_filter=original_filter)
    )
    transform = MagicMock()
    accounting = StageAccountingAccumulator()
    token = bind_stage_accounting(accounting)
    try:
        outcomes = [
            _build_gold_record(
                context=MagicMock(),
                silver_record={"assay_id": i},
                gold_filter=callback,
                gold_transform=transform,
            )
            for i in range(1000)
        ]
    finally:
        reset_stage_accounting(token)
    assert all(row == (None, False, None) for row in outcomes)
    original_filter.assert_not_called()
    transform.assert_not_called()
    metrics = {
        "records_fetched": 1000,
        "records_bronze": 1000,
        "records_silver": 1000,
        "records_gold": 0,
        "records_gold_excluded_by_contract": 0,
    }
    _seed_gold_removals_from_metrics(accounting, metrics)
    report = build_pipeline_run_report(
        identity={"status": "success"}, metrics=metrics, accounting=accounting
    )
    assert report.layers.gold_skipped == 1000
    assert report.layers.gold_excluded_by_contract == 0
    assert all(row.unaccounted == 0 for row in report.funnel)
    assert accounting.sum_outcome("gold", "skipped") == 1000
    assert accounting.unmapped_reason_count == 0
