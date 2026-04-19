"""Focused tests for postrun final metadata write helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.postrun._metadata_writes import (
    build_final_metadata_write_coroutines,
    get_run_statistics,
)
from bioetl.domain.config import PipelineConfig, RuntimeConfig, TableConfig
from bioetl.domain.types import RunType


def test_get_run_statistics_returns_empty_dict_without_hook() -> None:
    """Executors without a run-statistics hook should not break postrun writes."""
    executor = object()

    assert get_run_statistics(executor) == {}


@pytest.mark.asyncio
async def test_build_final_metadata_write_coroutines_builds_silver_only() -> None:
    """Silver metadata finalization should remain executable after extraction."""
    storage = MagicMock()
    storage.get_table_path = MagicMock(return_value="test-output/test_silver")
    storage.is_table_initialized = MagicMock(return_value=False)

    metadata_coordinator = MagicMock()
    metadata_writer = MagicMock()
    metadata_writer.finalize_silver_metadata = AsyncMock(return_value="silver.yaml")
    metadata_writer.finalize_gold_metadata = AsyncMock(return_value="gold.yaml")

    config = PipelineConfig(
        pipeline_name="test_postrun_pipeline",
        provider="chembl",
        entity_type="activity",
        table=TableConfig(
            primary_keys=("activity_id",),
            silver_table="silver_table",
            gold_table="gold_table",
        ),
    )
    runtime = RuntimeConfig(run_type=RunType.INCREMENTAL, skip_gold=True)
    context = MagicMock()
    context.started_at = datetime.now(UTC)

    coroutines = build_final_metadata_write_coroutines(
        metadata_coordinator=metadata_coordinator,
        metadata_writer=metadata_writer,
        storage=storage,
        config=config,
        runtime=runtime,
        context=context,
        stats={"records_silver": 5, "source_batch_ids": ["batch-1"]},
        dq_reports=None,
        completed_at=datetime.now(UTC),
        resolve_delta_version=lambda _table_path, layer: 7,
    )

    assert len(coroutines) == 1
    await coroutines[0]

    metadata_coordinator.create_silver_metadata.assert_not_called()
    metadata_writer.finalize_silver_metadata.assert_awaited_once()
    metadata_writer.finalize_gold_metadata.assert_not_awaited()
