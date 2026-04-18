"""Unit tests for BatchCheckpointRecoveryService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.batch_checkpoint_recovery_service import (
    BatchCheckpointRecoveryService,
)


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
