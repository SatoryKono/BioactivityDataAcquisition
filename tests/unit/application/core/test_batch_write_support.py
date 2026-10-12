# pyright: reportArgumentType=false
"""Unit tests for batch write-path helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core._batch_write_support import safe_write_layer

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_safe_write_layer_does_not_double_track_batch_failed() -> None:
    """Operation errors are tracked once via execute_with_span on_error."""

    writer = MagicMock()
    writer.write_silver = AsyncMock(side_effect=RuntimeError("write failed"))
    writer.track_batch_written = MagicMock()
    writer.track_batch_failed = MagicMock()
    writer.log_and_track_write_error = MagicMock()

    async def execute_with_span(
        _name: str,
        coro: object,
        _batch_id: object,
        _count: int,
        *,
        on_error: object,
    ) -> object:
        try:
            return await coro  # type: ignore[misc]
        except Exception as error:
            on_error(error)  # type: ignore[operator]
            raise

    with pytest.raises(RuntimeError, match="write failed"):
        await safe_write_layer(
            execute_with_span=execute_with_span,
            writer=writer,
            quarantine_manager=MagicMock(),
            logger=MagicMock(),
            run_id="run-1",  # type: ignore[arg-type]
            domain_event_emitter=None,
            layer="silver",
            records=[{"id": 1}],
            batch_id="batch-1",  # type: ignore[arg-type]
            ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
            bronze_refs=None,
            operation_errors=(RuntimeError,),
        )

    writer.log_and_track_write_error.assert_called_once()
    writer.track_batch_failed.assert_not_called()
