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
@pytest.mark.parametrize("with_batch_metrics", [True, False])
async def test_gold_schema_quarantine_preserves_silver_and_zero_gold(
    with_batch_metrics: bool,
) -> None:
    from bioetl.application.core._batch_processing_layer_write_support import (
        write_silver_then_gold,
    )
    from bioetl.domain.exceptions import SchemaViolationError

    accounting = StageAccountingAccumulator()
    token = bind_stage_accounting(accounting)
    metrics = BatchMetricsRecorderService(None, "pubmed_publication", "incremental")
    port = MagicMock(write_many=AsyncMock())
    quarantine = QuarantineRuntimeService(
        port,
        "pubmed_publication",
        batch_metrics=metrics if with_batch_metrics else None,
    )
    writer = MagicMock(
        write_silver=AsyncMock(return_value=True),
        write_gold=AsyncMock(side_effect=SchemaViolationError("gold", ["invalid"])),
    )

    async def execute_span(name, operation, *args, **kwargs):
        return await operation

    try:
        metrics.track_processed_records("bronze", 2)
        await write_silver_then_gold(
            execute_with_span=execute_span,
            writer=writer,
            quarantine_manager=quarantine,
            logger=MagicMock(),
            batch_metrics=metrics,
            run_id=None,
            domain_event_emitter=None,
            transform_result=MagicMock(silver_records=[{}, {}], gold_records=[{}, {}]),
            batch_id=BatchID(UUID("11111111-1111-4111-8111-111111111111")),
            ingestion_ts=datetime(2026, 9, 21, tzinfo=UTC),
            bronze_refs=None,
        )
        # Simulate the executor's prepared-record fallback; durable accounting
        # must override it even when the successful write count is zero.
        counters = {"records_gold": 2, **accounting.measured_record_metrics()}
        layers = accounting.snapshot_layers_from_metrics(counters)
        assert layers.bronze_records == layers.silver_valid == 2
        assert layers.silver_quarantined == 0
        assert layers.gold_written == 0
        assert layers.gold_quarantined == 2
        port.write_many.assert_awaited_once()
        writer.track_batch_written.assert_called_once_with(stage="silver", count=2)
    finally:
        reset_stage_accounting(token)


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
    port = MagicMock(write_many=AsyncMock(side_effect=[OSError("disk full"), None]))
    quarantine = QuarantineRuntimeService(
        port,
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
        # Retry the failed durable write, then republish the same completed
        # accounting snapshot. Neither projection may add another removal.
        await quarantine.quarantine_records(
            [outcome.dq_entry],
            BatchID(UUID("11111111-1111-4111-8111-111111111111")),
            ingestion_ts=datetime(2026, 9, 21, tzinfo=UTC),
        )
        for _ in range(3):
            measured = accounting.measured_record_metrics()
            assert measured["records_quarantined"] == 1
            layers = accounting.snapshot_layers_from_metrics(
                {"records_bronze": 1, **measured}
            )
            silver = accounting.snapshot_funnel(layers)[2]
            assert silver.removed_total == 1
            assert silver.records_in == silver.records_out + silver.removed_total
        assert port.write_many.await_count == 2
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


@pytest.mark.asyncio
async def test_hard_threshold_persists_quarantine_before_abort() -> None:
    from types import SimpleNamespace
    from bioetl.application.core.batch_transformer_finalization import (
        finalize_batch_transform_result,
    )
    from bioetl.application.core.batch_transformer_state import (
        TransformAggregationState,
    )
    from bioetl.domain.exceptions.data_quality import DataQualityThresholdError

    accounting = StageAccountingAccumulator()
    token = bind_stage_accounting(accounting)
    metrics = BatchMetricsRecorderService(
        None, "chembl_assay_parameters", "incremental"
    )
    port = MagicMock(write_many=AsyncMock())
    quarantine = QuarantineRuntimeService(
        port, "chembl_assay_parameters", batch_metrics=metrics
    )
    record = {"id": 1}
    try:
        outcome = handle_data_quality_transform_error(
            ValueError("invalid"),
            error_type=ErrorType.SCHEMA_VIOLATION,
            batch_metrics=metrics,
            dq_config=None,
            raw_record=record,
            debug_export_service=None,
            index=0,
        )

        async def flush():
            await quarantine.quarantine_records(
                [outcome.dq_entry],
                BatchID(UUID("11111111-1111-4111-8111-111111111111")),
                ingestion_ts=datetime(2026, 9, 21, tzinfo=UTC),
            )
            return 0

        with pytest.raises(DataQualityThresholdError):
            await finalize_batch_transform_result(
                context=SimpleNamespace(logger=MagicMock()),
                config=SimpleNamespace(
                    dq_config=SimpleNamespace(soft_threshold=0.1, hard_threshold=0.5)
                ),
                batch_metrics=metrics,
                state=TransformAggregationState(silver_records=[], gold_records=[]),
                records=[record],
                flush_filtered_records=AsyncMock(return_value=0),
                flush_dq_records=flush,
            )
        port.write_many.assert_awaited_once()
        assert accounting.measured_record_metrics()["records_quarantined"] == 1
    finally:
        reset_stage_accounting(token)


@pytest.mark.asyncio
@pytest.mark.parametrize("previous", [None, "OK", "ERROR"])
async def test_no_gold_candidates_records_not_applicable_without_erasing_checks(
    previous,
):
    from bioetl.application.core._batch_processing_layer_write_support import (
        write_silver_then_gold,
    )
    from bioetl.application.services.run_reports.observations import (
        bind_run_observations,
        reset_run_observations,
        record_run_observation,
        run_observations,
    )

    token = bind_run_observations()

    async def execute_span(name, operation, *args, **kwargs):
        return await operation

    writer = MagicMock(
        write_silver=AsyncMock(return_value=True), write_gold=AsyncMock()
    )
    try:
        if previous:
            record_run_observation(
                "Data Validation", verdict=previous, reason="prior_batch", facts={}
            )
        await write_silver_then_gold(
            execute_with_span=execute_span,
            writer=writer,
            quarantine_manager=MagicMock(),
            logger=MagicMock(),
            batch_metrics=BatchMetricsRecorderService(
                None, "chembl_molecule", "backfill"
            ),
            run_id=None,
            domain_event_emitter=None,
            transform_result=MagicMock(silver_records=[{}], gold_records=[]),
            batch_id=BatchID(UUID("11111111-1111-4111-8111-111111111111")),
            ingestion_ts=datetime(2026, 9, 25, tzinfo=UTC),
            bronze_refs=None,
        )
        observation = run_observations()["Data Validation"]
        assert observation["verdict"] == (previous or "N/A")
        if previous is None:
            assert observation["reason"] == "no_gold_candidates"
        writer.write_gold.assert_not_awaited()
    finally:
        reset_run_observations(token)
