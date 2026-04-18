"""Unit tests for Silver metadata operations service."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.infrastructure.storage.silver.operations.metadata_operations import (
    SilverMetadataOperations,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_silver_metadata_uses_record_ingestion_anchor_when_explicit_time_missing() -> (
    None
):
    """Metadata runtime timestamps should reuse deterministic record anchors."""
    expected = datetime(2025, 1, 15, 12, 0, tzinfo=UTC)
    captured: dict[str, object] = {}

    async def capture_write(**kwargs):
        await asyncio.sleep(0)
        captured.update(kwargs)
        return None

    metadata_writer = MagicMock()
    metadata_writer.write_silver_metadata = capture_write
    ops = SilverMetadataOperations(
        _logger=MagicMock(),
        _metadata_writer=metadata_writer,
    )

    await ops.write_silver_metadata(
        table_name="chembl.activity",
        dq_metrics=BatchDQMetrics(
            total_records=1,
            valid_records=1,
            error_records=0,
            warning_records=0,
        ),
        records=[
            {
                "entity_id": "CHEMBL1",
                "_ingestion_ts": expected.isoformat(),
            }
        ],
    )

    metadata = captured["metadata"]
    assert metadata.runtime.started_at_utc == expected
    assert metadata.runtime.completed_at_utc == expected
