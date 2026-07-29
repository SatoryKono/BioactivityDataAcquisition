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
) -> None:
    await service.save_periodic_checkpoint(
        records_fetched=3,
        resume_offset=10,
        checkpoint_interval=5,
    )

    checkpoint_manager.save_checkpoint.assert_not_called()


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
