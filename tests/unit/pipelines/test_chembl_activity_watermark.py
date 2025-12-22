"""Unit tests for ChEMBL activity pipeline watermark extraction."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline
from bioetl.domain.config import PipelineConfig, RuntimeConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunID, RunType, Watermark


@pytest.fixture
def chembl_pipeline() -> ChEMBLActivityPipeline:
    """Создает пайплайн ChEMBL с детерминированным watermark."""

    config = PipelineConfig(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type="activity",
        primary_keys=["activity_id"],
        silver_table="chembl_activity",
        batch_size=10,
        checkpoint_interval=5,
        watermark_field="updated_on",
    )

    runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)

    logger = MagicMock()
    logger.bind.return_value = MagicMock()

    services = PipelineServices(
        data_source=AsyncMock(),
        storage=AsyncMock(),
        lock=AsyncMock(),
        checkpoint=AsyncMock(),
        quarantine=AsyncMock(),
        metrics=MagicMock(),
        tracing=MagicMock(),
        logger=logger,
    )

    return ChEMBLActivityPipeline(config=config, runtime=runtime, services=services)


@pytest.fixture
def context(chembl_pipeline: ChEMBLActivityPipeline) -> PipelineContext:
    """Возвращает PipelineContext с тестовым run_id."""

    return PipelineContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        logger=chembl_pipeline.logger,
    )


def test_extract_watermark_with_activity_id(
    chembl_pipeline: ChEMBLActivityPipeline, context: PipelineContext
) -> None:
    """Возвращает activity_id как строку wrapped в Watermark."""

    record = {"activity_id": 123, "updated_on": "2024-01-01T00:00:00+00:00"}

    watermark = chembl_pipeline.extract_watermark(context, record)

    assert isinstance(watermark, Watermark)
    assert watermark.value == "123"


def test_extract_watermark_with_fallback_field(
    chembl_pipeline: ChEMBLActivityPipeline, context: PipelineContext
) -> None:
    """Парсит updated_on из конфигурации в datetime UTC wrapped в Watermark."""

    record = {"updated_on": "2024-02-02T10:00:00"}

    watermark = chembl_pipeline.extract_watermark(context, record)

    assert isinstance(watermark, Watermark)
    assert isinstance(watermark.value, datetime)
    assert watermark.value.tzinfo is UTC
    assert watermark.value == datetime(2024, 2, 2, 10, 0, tzinfo=UTC)


def test_extract_watermark_without_cursor_fields(
    chembl_pipeline: ChEMBLActivityPipeline, context: PipelineContext
) -> None:
    """Возвращает пустую строку wrapped в Watermark без доступных курсоров."""

    watermark = chembl_pipeline.extract_watermark(context, {})

    assert isinstance(watermark, Watermark)
    assert watermark.value == ""


@pytest.mark.asyncio
async def test_checkpoint_watermark_idempotent(
    chembl_pipeline: ChEMBLActivityPipeline, context: PipelineContext
) -> None:
    """CheckpointManager сохраняет одинаковый watermark для одинаковых записей."""

    checkpoint_port = AsyncMock()
    checkpoint_port.load = AsyncMock(return_value=None)

    manager = CheckpointManager(
        checkpoint_port=checkpoint_port,
        logger=chembl_pipeline.logger,
        pipeline_name=chembl_pipeline.pipeline_name,
        run_id=chembl_pipeline.run_id,
        resume=True,
        watermark_extractor=lambda record: chembl_pipeline.extract_watermark(
            context, record
        ),
    )

    record = {"updated_on": "2024-03-03T12:30:00+00:00"}

    await manager.save_checkpoint(last_record=record, records_processed=1)
    await manager.save_checkpoint(last_record=record, records_processed=2)

    first_watermark = checkpoint_port.save.call_args_list[0].kwargs["watermark"]
    second_watermark = checkpoint_port.save.call_args_list[1].kwargs["watermark"]

    assert first_watermark == second_watermark
