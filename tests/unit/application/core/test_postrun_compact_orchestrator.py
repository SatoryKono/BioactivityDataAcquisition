"""Tests for PostrunCompactService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.postrun.compact_orchestrator import (
    CompactionResult,
    PostrunCompactService,
)
from bioetl.domain.exceptions import BioETLError, DeltaWriteConflictError
from bioetl.domain.medallion import SilverWriteMode


def _make_config(
    *,
    silver_write_mode: SilverWriteMode = SilverWriteMode.APPEND,
    silver_table: str = "chembl/activity",
    primary_keys: tuple[str, ...] = ("activity_id",),
) -> MagicMock:
    config = MagicMock()
    config.table.silver_write_mode = silver_write_mode
    config.table.primary_keys = primary_keys
    config.effective_silver_table = silver_table
    config.pipeline_name = "chembl_activity"
    return config


def _make_service(
    config: MagicMock | None = None,
    dedup_result: int = 0,
) -> PostrunCompactService:
    if config is None:
        config = _make_config()
    storage = MagicMock()
    storage.deduplicate_silver = AsyncMock(return_value=dedup_result)
    storage.optimize = AsyncMock()
    logger = MagicMock()
    return PostrunCompactService(
        config=config,
        storage=storage,
        logger=logger,
        warning_allowlist=(RuntimeError, ValueError),
    )


@pytest.mark.asyncio
async def test_runs_dedup_for_merge_mode() -> None:
    config = _make_config(silver_write_mode=SilverWriteMode.MERGE)
    svc = _make_service(config=config)
    result = await svc.run_if_needed()
    assert result == CompactionResult(status="success", duplicates_removed=0)


@pytest.mark.asyncio
async def test_skips_when_no_silver_table() -> None:
    config = _make_config(silver_table="")
    svc = _make_service(config=config)
    result = await svc.run_if_needed()
    assert result == CompactionResult(status="skipped")


@pytest.mark.asyncio
async def test_skips_when_no_primary_keys() -> None:
    config = _make_config(primary_keys=())
    svc = _make_service(config=config)
    result = await svc.run_if_needed()
    assert result == CompactionResult(status="skipped")


@pytest.mark.asyncio
async def test_calls_deduplicate_silver() -> None:
    svc = _make_service(dedup_result=42)
    result = await svc.run_if_needed()
    assert result == CompactionResult(status="success", duplicates_removed=42)
    svc._storage.deduplicate_silver.assert_awaited_once_with(
        "chembl/activity", ["activity_id"]
    )


@pytest.mark.asyncio
async def test_catches_allowlisted_exceptions() -> None:
    config = _make_config()
    storage = MagicMock()
    storage.deduplicate_silver = AsyncMock(side_effect=RuntimeError("boom"))
    storage.optimize = AsyncMock()
    logger = MagicMock()
    svc = PostrunCompactService(
        config=config,
        storage=storage,
        logger=logger,
        warning_allowlist=(RuntimeError,),
    )
    result = await svc.run_if_needed()
    assert result == CompactionResult(status="failed", error="boom")
    logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_catches_allowlisted_timeout_error() -> None:
    config = _make_config()
    storage = MagicMock()
    storage.deduplicate_silver = AsyncMock(side_effect=TimeoutError("timed out"))
    storage.optimize = AsyncMock()
    logger = MagicMock()
    svc = PostrunCompactService(
        config=config,
        storage=storage,
        logger=logger,
        warning_allowlist=(TimeoutError,),
    )
    result = await svc.run_if_needed()
    assert result == CompactionResult(status="failed", error="timed out")
    logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_catches_allowlisted_delta_write_conflicts() -> None:
    config = _make_config()
    storage = MagicMock()
    storage.deduplicate_silver = AsyncMock(
        side_effect=DeltaWriteConflictError(
            "/tmp/chembl/activity",
            operation="deduplicate",
        )
    )
    storage.optimize = AsyncMock()
    logger = MagicMock()
    svc = PostrunCompactService(
        config=config,
        storage=storage,
        logger=logger,
        warning_allowlist=(BioETLError,),
    )
    result = await svc.run_if_needed()
    assert result.status == "failed"
    assert result.error is not None
    assert "during deduplicate" in result.error
    logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_raises_non_allowlisted_exceptions() -> None:
    config = _make_config()
    storage = MagicMock()
    storage.deduplicate_silver = AsyncMock(side_effect=TypeError("bad"))
    storage.optimize = AsyncMock()
    logger = MagicMock()
    svc = PostrunCompactService(
        config=config,
        storage=storage,
        logger=logger,
        warning_allowlist=(RuntimeError,),
    )
    with pytest.raises(TypeError, match="bad"):
        await svc.run_if_needed()
