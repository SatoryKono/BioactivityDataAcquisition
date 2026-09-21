"""Regression: one rejected record remains one removal after quarantine writes."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.application.core.base_transformer import FilteredOutError
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_transformer_attempt_failures import (
    _build_filtered_out_handling_context,
    handle_data_quality_transform_error,
    handle_filtered_out_error,
)
from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.domain.run_reports.context import (
    bind_stage_accounting,
    reset_stage_accounting,
)
from bioetl.domain.types import BatchID, ErrorType

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize("filtered", [True, False])
async def test_rejection_and_durable_quarantine_count_once(filtered: bool) -> None:
    accounting = StageAccountingAccumulator()
    token = bind_stage_accounting(accounting)
    metrics = BatchMetricsRecorderService(None, "chembl_activity", "incremental")
    port = MagicMock(write_many=AsyncMock())
    quarantine = QuarantineRuntimeService(
        port, "chembl_activity", batch_metrics=metrics
    )
    batch_id = BatchID(UUID("11111111-1111-4111-8111-111111111111"))
    try:
        if filtered:
            outcome = handle_filtered_out_error(
                FilteredOutError("excluded"),
                _build_filtered_out_handling_context(metrics, None, {"id": 1}, None, 0),
            )
            await quarantine.quarantine_filtered_records(
                [outcome.filtered_entry],
                batch_id,
                ingestion_ts=datetime(2026, 9, 21, tzinfo=UTC),
            )
        else:
            outcome = handle_data_quality_transform_error(
                ValueError("invalid"),
                error_type=ErrorType.SCHEMA_VIOLATION,
                batch_metrics=metrics,
                dq_config=None,
                raw_record={"id": 1},
                debug_export_service=None,
                index=0,
            )
            await quarantine.quarantine_records(
                [outcome.dq_entry],
                batch_id,
                ingestion_ts=datetime(2026, 9, 21, tzinfo=UTC),
            )
        layers = accounting.snapshot_layers_from_metrics({"records_bronze": 1})
        assert layers.silver_filtered_out == int(filtered)
        assert layers.silver_quarantined == int(not filtered)
        assert sum(r.count for r in accounting.snapshot_funnel(layers)[2].removals) == 1
        port.write_many.assert_awaited_once()
    finally:
        reset_stage_accounting(token)


@pytest.mark.asyncio
async def test_failed_quarantine_write_does_not_claim_durable_removal() -> None:
    accounting = StageAccountingAccumulator()
    token = bind_stage_accounting(accounting)
    metrics = BatchMetricsRecorderService(None, "chembl_activity", "incremental")
    quarantine = QuarantineRuntimeService(
        MagicMock(write_many=AsyncMock(side_effect=OSError("disk full"))),
        "chembl_activity",
        batch_metrics=metrics,
    )
    try:
        outcome = handle_data_quality_transform_error(
            ValueError("invalid"),
            error_type=ErrorType.SCHEMA_VIOLATION,
            batch_metrics=metrics,
            dq_config=None,
            raw_record={"id": 1},
            debug_export_service=None,
            index=0,
        )
        with pytest.raises(OSError, match="disk full"):
            await quarantine.quarantine_records(
                [outcome.dq_entry],
                BatchID(UUID("11111111-1111-4111-8111-111111111111")),
                ingestion_ts=datetime(2026, 9, 21, tzinfo=UTC),
            )
        assert "records_quarantined" not in accounting.measured_record_metrics()
    finally:
        reset_stage_accounting(token)


def test_failed_batch_retains_durable_bronze_before_transform() -> None:
    from bioetl.application.core._batch_processing_metrics_support import (
        track_bronze_write_metrics,
        track_transform_result_metrics,
    )
    from bioetl.application.core.runner import PipelineRunner

    accounting = StageAccountingAccumulator()
    token = bind_stage_accounting(accounting)
    metrics = BatchMetricsRecorderService(None, "chembl_activity", "incremental")
    runner = object.__new__(PipelineRunner)
    runner._executor = MagicMock(
        records_fetched=1000,
        records_bronze=0,
        records_silver=0,
        records_gold=0,
        records_quarantined=0,
        records_filtered_out=0,
        records_gold_excluded_by_contract=0,
    )
    try:
        track_bronze_write_metrics(metrics, record_count=1000)
        # Transform-ready records are not durable Silver/Gold writes.
        result = MagicMock(
            silver_records=[{}], gold_records=[{}], gold_excluded_by_contract_count=0
        )
        track_transform_result_metrics(metrics, transform_result=result)
        assert runner.execution_metrics["records_bronze"] == 1000
        assert runner.execution_metrics["records_silver"] == 0
        assert runner.execution_metrics["records_gold"] == 0
    finally:
        reset_stage_accounting(token)
