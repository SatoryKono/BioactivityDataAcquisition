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
"""Unit tests for BatchCheckpointRecoveryService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.batch_checkpoint_recovery_service import (
    BatchCheckpointRecoveryService,
)
from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
from bioetl.domain.config import MemoryConfig
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


@pytest.fixture
def checkpoint_manager() -> AsyncMock:
    manager = AsyncMock()
    manager.save_checkpoint = AsyncMock()
    manager._operation_errors = (RuntimeError,)
    return manager


@pytest.fixture
def logger() -> MagicMock:
    mock = MagicMock()
    mock.warning = MagicMock()
    return mock


@pytest.fixture
def metrics() -> MagicMock:
    mock = MagicMock()
    mock.increment_counter = MagicMock()
    mock.observe_histogram = MagicMock()
    mock.set_gauge = MagicMock()
    return mock


@pytest.fixture
def tracer() -> MagicMock:
    span = MagicMock()
    otel = MagicMock()
    otel.start_as_current_span.return_value = span
    mock = MagicMock()
    mock.get_tracer.return_value = otel
    return mock


@pytest.fixture
def service(
    checkpoint_manager: AsyncMock,
    logger: MagicMock,
    metrics: MagicMock,
    tracer: MagicMock,
) -> BatchCheckpointRecoveryService:
    return BatchCheckpointRecoveryService(
        checkpoint_manager=checkpoint_manager,
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        pipeline_name="chembl_activity",
    )


@pytest.mark.asyncio
async def test_save_periodic_checkpoint_skips_when_interval_not_reached(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
    metrics: MagicMock,
) -> None:
    await service.save_periodic_checkpoint(
        records_fetched=3,
        resume_offset=10,
        checkpoint_interval=5,
    )

    checkpoint_manager.save_checkpoint.assert_not_called()
    metrics.increment_counter.assert_called_once_with(
        "bioetl_checkpoint_save_events_total",
        1,
        {"pipeline": "chembl_activity", "operation": "periodic", "status": "skipped"},
    )


@pytest.mark.asyncio
async def test_save_periodic_checkpoint_skips_nonpositive_interval(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
) -> None:
    await service.save_periodic_checkpoint(
        records_fetched=10,
        resume_offset=0,
        checkpoint_interval=0,
    )

    checkpoint_manager.save_checkpoint.assert_not_called()


@pytest.mark.asyncio
async def test_resume_checkpoint_uses_confirmed_count_plus_offset(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
) -> None:
    """Resume offset is confirmed_count + resume_offset (#11221 supersedes #11168)."""
    await service.save_periodic_checkpoint(
        records_fetched=10,
        resume_offset=7,
        checkpoint_interval=5,
    )
    await service.save_checkpoint_on_exception(
        records_fetched=10,
        resume_offset=7,
        error=RuntimeError("boom"),
    )
    await service.save_checkpoint_on_shutdown(records_fetched=10, resume_offset=7)

    assert [
        call.args for call in checkpoint_manager.save_checkpoint.await_args_list
    ] == [
        (17,),
        (17,),
        (17,),
    ]


@pytest.mark.asyncio
async def test_save_periodic_checkpoint_persists_total_processed(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
) -> None:
    await service.save_periodic_checkpoint(
        records_fetched=10,
        resume_offset=7,
        checkpoint_interval=5,
    )

    checkpoint_manager.save_checkpoint.assert_awaited_once_with(17)


@pytest.mark.asyncio
async def test_save_checkpoint_on_exception_skips_zero_totals(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
    metrics: MagicMock,
) -> None:
    await service.save_checkpoint_on_exception(
        records_fetched=0,
        resume_offset=0,
        error=RuntimeError("boom"),
    )

    checkpoint_manager.save_checkpoint.assert_not_called()
    metrics.increment_counter.assert_called_once_with(
        "bioetl_checkpoint_save_events_total",
        1,
        {
            "pipeline": "chembl_activity",
            "operation": "exception",
            "status": "skipped",
        },
    )


@pytest.mark.asyncio
async def test_save_checkpoint_on_exception_logs_recovery_warning(
    service: BatchCheckpointRecoveryService,
    logger: MagicMock,
) -> None:
    await service.save_checkpoint_on_exception(
        records_fetched=4,
        resume_offset=6,
        error=ValueError("bad row"),
    )

    logger.warning.assert_called_once()
    kwargs = logger.warning.call_args.kwargs
    assert kwargs["records_processed"] == 10
    assert kwargs["error_type"] == "ValueError"


@pytest.mark.asyncio
async def test_save_checkpoint_on_shutdown_logs_checkpoint_error(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
    logger: MagicMock,
) -> None:
    checkpoint_manager.save_checkpoint.side_effect = RuntimeError("disk unavailable")

    await service.save_checkpoint_on_shutdown(
        records_fetched=4,
        resume_offset=6,
    )

    logger.warning.assert_called_once()
    assert logger.warning.call_args.kwargs == {
        "records_processed": 10,
        "error_type": "RuntimeError",
        "reason": "checkpoint_save_failed_on_shutdown",
    }


@pytest.mark.asyncio
async def test_save_checkpoint_now_persists_total_processed(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
) -> None:
    await service.save_checkpoint_now(
        records_fetched=12,
        resume_offset=8,
    )

    checkpoint_manager.save_checkpoint.assert_awaited_once_with(20)


@pytest.mark.asyncio
async def test_save_checkpoint_persists_memory_decision_trace(
    checkpoint_manager: AsyncMock,
    logger: MagicMock,
    metrics: MagicMock,
) -> None:
    memory_manager = BatchMemoryManagerService(
        initial_batch_size=1000,
        memory_config=MemoryConfig(max_batch_memory_mb=1, min_batch_size=50),
    )
    memory_manager.check_pressure(
        current_size=2000,
        check_interval=100,
        records_fetched=100,
    )
    service = BatchCheckpointRecoveryService(
        checkpoint_manager=checkpoint_manager,
        logger=logger,
        metrics=metrics,
        pipeline_name="chembl_activity",
        memory_manager=memory_manager,
    )

    await service.save_checkpoint_now(records_fetched=100, resume_offset=0)

    checkpoint_manager.save_checkpoint.assert_awaited_once()
    payload = checkpoint_manager.save_checkpoint.await_args.args[0]
    assert isinstance(payload, CheckpointMetadata)
    assert payload.records_processed == 100
    assert payload.memory_decision_trace[0]["stage"] == "pressure_check"
    assert payload.memory_decision_trace[0]["reason"] == "config_budget_exceeded"
    assert payload.memory_decision_trace[0]["pressure_state"] is True
    assert payload.memory_decision_trace[0]["monitor_mode"] == "config_budget"


@pytest.mark.asyncio
async def test_save_checkpoint_now_leaves_checkpoint_saved_at_gauge_to_manager(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
    metrics: MagicMock,
) -> None:
    await service.save_checkpoint_now(
        records_fetched=1,
        resume_offset=0,
    )

    checkpoint_manager.save_checkpoint.assert_awaited_once_with(1)
    metrics.set_gauge.assert_not_called()


@pytest.mark.asyncio
async def test_save_checkpoint_failure_emits_failed_telemetry_and_span(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
    metrics: MagicMock,
    tracer: MagicMock,
) -> None:
    checkpoint_manager.save_checkpoint.side_effect = RuntimeError("disk full")

    with pytest.raises(RuntimeError, match="disk full"):
        await service.save_checkpoint_now(records_fetched=2, resume_offset=3)

    metrics.increment_counter.assert_called_once_with(
        "bioetl_checkpoint_save_events_total",
        1,
        {
            "pipeline": "chembl_activity",
            "operation": "manual",
            "status": "failed",
        },
    )
    metrics.observe_histogram.assert_called_once()
    span = tracer.get_tracer.return_value.start_as_current_span.return_value
    span.set_attribute.assert_any_call("bioetl.checkpoint.status", "failed")
    span.set_attribute.assert_any_call("error", True)
    span.record_exception.assert_called_once()
    span.__exit__.assert_called_once_with(None, None, None)


@pytest.mark.asyncio
async def test_exception_checkpoint_failure_is_contained_and_logged(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
    logger: MagicMock,
) -> None:
    checkpoint_manager.save_checkpoint.side_effect = RuntimeError("disk full")

    await service.save_checkpoint_on_exception(
        records_fetched=4,
        resume_offset=6,
        error=ValueError("bad row"),
    )

    logger.warning.assert_called_once()
    assert logger.warning.call_args.kwargs == {
        "records_processed": 10,
        "error_type": "RuntimeError",
        "reason": "checkpoint_save_failed_on_pipeline_exception",
    }


@pytest.mark.asyncio
async def test_shutdown_checkpoint_failure_is_contained_and_logged(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
    logger: MagicMock,
) -> None:
    checkpoint_manager.save_checkpoint.side_effect = RuntimeError("disk full")

    await service.save_checkpoint_on_shutdown(records_fetched=5, resume_offset=7)

    logger.warning.assert_called_once()
    assert logger.warning.call_args.kwargs == {
        "records_processed": 12,
        "error_type": "RuntimeError",
        "reason": "checkpoint_save_failed_on_shutdown",
    }


@pytest.mark.asyncio
async def test_checkpoint_without_optional_observability_still_persists(
    checkpoint_manager: AsyncMock,
    logger: MagicMock,
) -> None:
    service = BatchCheckpointRecoveryService(
        checkpoint_manager=checkpoint_manager,
        logger=logger,
        pipeline_name="chembl_activity",
    )

    await service.save_checkpoint_now(records_fetched=1, resume_offset=2)

    checkpoint_manager.save_checkpoint.assert_awaited_once_with(3)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shutdown_checkpoint_failure_is_recorded(
    checkpoint_manager: AsyncMock,
    logger: MagicMock,
    metrics: MagicMock,
    tracer: MagicMock,
) -> None:
    """Ошибка shutdown checkpoint локализуется и наблюдаема."""
    checkpoint_manager._operation_errors = (OSError,)
    checkpoint_manager.save_checkpoint.side_effect = OSError("disk unavailable")
    recovery_service = BatchCheckpointRecoveryService(
        checkpoint_manager=checkpoint_manager,
        logger=logger,
        metrics=metrics,
        tracer=tracer,
        pipeline_name="chembl_activity",
    )

    await recovery_service.save_checkpoint_on_shutdown(
        records_fetched=4,
        resume_offset=6,
    )

    logger.warning.assert_called_once()
    assert logger.warning.call_args.kwargs["records_processed"] == 10
    assert logger.warning.call_args.kwargs["error_type"] == "OSError"
    metrics.increment_counter.assert_called_once()
    metrics.observe_histogram.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resume_checkpoints_use_fetched_count_plus_offset(
    checkpoint_manager: AsyncMock,
    logger: MagicMock,
) -> None:
    """Shutdown, exception, and periodic checkpoints share the fetched-count contract."""
    recovery_service = BatchCheckpointRecoveryService(
        checkpoint_manager=checkpoint_manager,
        logger=logger,
        pipeline_name="chembl_activity",
    )

    await recovery_service.save_checkpoint_on_shutdown(
        records_fetched=4,
        resume_offset=10,
    )
    await recovery_service.save_checkpoint_on_exception(
        records_fetched=4,
        resume_offset=10,
        error=RuntimeError("extract failed"),
    )
    # Boundary p=4 is already durable (shutdown + exception saves), so the
    # periodic call must present new confirmed progress to trigger a save.
    await recovery_service.save_periodic_checkpoint(
        records_fetched=6,
        resume_offset=10,
        checkpoint_interval=2,
    )

    assert checkpoint_manager.save_checkpoint.await_count == 3
    assert [
        call.args[0] for call in checkpoint_manager.save_checkpoint.await_args_list
    ] == [14, 14, 16]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resume_checkpoint_uses_fetched_count_plus_offset(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
) -> None:
    """Resume stores fetched records plus the prior offset, not a Bronze count."""
    await service.save_periodic_checkpoint(
        records_fetched=4,
        resume_offset=10,
        checkpoint_interval=2,
    )
    await service.save_checkpoint_on_exception(
        records_fetched=4,
        resume_offset=10,
        error=RuntimeError("boom"),
    )
    await service.save_checkpoint_on_shutdown(records_fetched=4, resume_offset=10)

    assert checkpoint_manager.save_checkpoint.await_count == 3
    for call in checkpoint_manager.save_checkpoint.await_args_list:
        assert call.args == (14,)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_periodic_checkpoint_uses_confirmed_progress_delta_not_modulo(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
) -> None:
    """batch=3000 / interval=5000 must still checkpoint at totals 6000/12000."""
    for confirmed_bronze in (3000, 6000, 9000, 12000, 15000):
        await service.save_periodic_checkpoint(
            records_fetched=confirmed_bronze,
            resume_offset=0,
            checkpoint_interval=5000,
        )

    assert [
        call.args[0] for call in checkpoint_manager.save_checkpoint.await_args_list
    ] == [6000, 12000]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_periodic_checkpoint_failed_save_does_not_advance_watermark(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
) -> None:
    """A failed save leaves the watermark behind; retry at same progress saves."""
    checkpoint_manager.save_checkpoint.side_effect = RuntimeError("disk unavailable")

    try:
        await service.save_periodic_checkpoint(
            records_fetched=5000,
            resume_offset=0,
            checkpoint_interval=5000,
        )
    except RuntimeError:
        pass

    checkpoint_manager.save_checkpoint.side_effect = None
    await service.save_periodic_checkpoint(
        records_fetched=5000,
        resume_offset=0,
        checkpoint_interval=5000,
    )

    assert [
        call.args[0] for call in checkpoint_manager.save_checkpoint.await_args_list
    ] == [5000, 5000]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_periodic_checkpoint_no_new_progress_skips(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
) -> None:
    """Repeated calls at unchanged progress persist once."""
    for _ in range(3):
        await service.save_periodic_checkpoint(
            records_fetched=8000,
            resume_offset=0,
            checkpoint_interval=5000,
        )

    assert checkpoint_manager.save_checkpoint.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manual_save_shares_watermark_with_periodic(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
) -> None:
    """Every operation persists the same boundary, so all share the watermark."""
    await service.save_checkpoint_now(records_fetched=9000, resume_offset=0)
    await service.save_periodic_checkpoint(
        records_fetched=10000,
        resume_offset=0,
        checkpoint_interval=5000,
    )
    await service.save_periodic_checkpoint(
        records_fetched=14000,
        resume_offset=0,
        checkpoint_interval=5000,
    )

    assert [
        call.args[0] for call in checkpoint_manager.save_checkpoint.await_args_list
    ] == [9000, 14000]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_periodic_checkpoint_resumed_run_counts_new_progress(
    service: BatchCheckpointRecoveryService,
    checkpoint_manager: AsyncMock,
) -> None:
    """Resumed run saves once per-run progress gains interval; payload stays absolute."""
    await service.save_periodic_checkpoint(
        records_fetched=1000,
        resume_offset=20000,
        checkpoint_interval=5000,
    )
    await service.save_periodic_checkpoint(
        records_fetched=6000,
        resume_offset=20000,
        checkpoint_interval=5000,
    )

    assert [
        call.args[0] for call in checkpoint_manager.save_checkpoint.await_args_list
    ] == [26000]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_canonical_loop_reaches_watermark_with_oversized_batch(
    checkpoint_manager: AsyncMock,
    logger: MagicMock,
) -> None:
    """#12098 reachability: canonical loop forwards confirmed Bronze progress.

    batch=3000 / interval=5000 — the old modulo model saved only at 15000;
    the delta model must save at confirmed totals 6000 and 12000.
    """
    from bioetl.application.core.batch_executor_loop_flow import (
        process_extracted_record_iteration,
    )
    from bioetl.application.core.batch_executor_loop_helpers import (
        BatchExtractionIterationContext,
        BatchExtractionLoopState,
    )

    recovery_service = BatchCheckpointRecoveryService(
        checkpoint_manager=checkpoint_manager,
        logger=logger,
        pipeline_name="chembl_activity",
    )
    progress_state = MagicMock(
        records_fetched=0,
        records_bronze=0,
        records_silver=0,
        records_filtered_out=0,
    )

    async def _process_batch(records: list[object], start_index: int) -> None:
        progress_state.records_bronze += len(records)
        progress_state.records_fetched = start_index + len(records)

    memory_manager = MagicMock()
    memory_manager.maybe_recover.side_effect = lambda size: size
    iteration_context = BatchExtractionIterationContext(
        checkpoint_recovery_service=recovery_service,
        resume_offset=0,
        process_batch=_process_batch,
        memory_manager=memory_manager,
        progress_service=MagicMock(),
        progress_state=progress_state,
        checkpoint_interval=5000,
    )
    loop_state = BatchExtractionLoopState(current_batch_size=3000, check_interval=10)

    records_fetched = 0
    for index in range(15000):
        records_fetched = await process_extracted_record_iteration(
            loop_state=loop_state,
            raw_record={"id": str(index)},
            shutdown_requested=False,
            records_fetched=records_fetched,
            update_batch_size=lambda _n: 3000,
            iteration_context=iteration_context,
        )

    assert [
        call.args[0] for call in checkpoint_manager.save_checkpoint.await_args_list
    ] == [6000, 12000]
