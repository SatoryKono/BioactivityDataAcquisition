"""ARCH-CR-04: medallion finalize_run vacuum counts and failure propagation."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bioetl.application.services.medallion.medallion_lifecycle import (
    MedallionLifecycleService,
)
from bioetl.domain.exceptions import StorageError


@pytest.mark.asyncio
async def test_finalize_run_returns_vacuum_counts_on_success() -> None:
    storage = AsyncMock()
    storage.vacuum = AsyncMock(side_effect=[3, 5])
    logger = SimpleNamespace(
        info=lambda *a, **k: None,
        error=lambda *a, **k: None,
        debug=lambda *a, **k: None,
    )
    service = MedallionLifecycleService(storage=storage, logger=logger)  # type: ignore[arg-type]
    config = SimpleNamespace(
        pipeline_name="chembl_activity",
        effective_silver_table="silver_activity",
        effective_gold_table="gold_activity",
    )
    runtime = SimpleNamespace(
        optimize_storage=True,
        vacuum_after_run=False,
        vacuum_retention_days=7,
        dry_run=False,
    )

    result = await service.finalize_run(config, runtime)  # type: ignore[arg-type]
    assert result.skipped is False
    assert result.silver_files_removed == 3
    assert result.gold_files_removed == 5
    assert storage.vacuum.await_count == 2


@pytest.mark.asyncio
async def test_finalize_run_reraises_storage_failure() -> None:
    storage = AsyncMock()
    storage.vacuum = AsyncMock(side_effect=StorageError("vacuum failed"))
    logger = SimpleNamespace(
        info=lambda *a, **k: None,
        error=lambda *a, **k: None,
        debug=lambda *a, **k: None,
    )
    service = MedallionLifecycleService(storage=storage, logger=logger)  # type: ignore[arg-type]
    config = SimpleNamespace(
        pipeline_name="chembl_activity",
        effective_silver_table="silver_activity",
        effective_gold_table="gold_activity",
    )
    runtime = SimpleNamespace(
        optimize_storage=True,
        vacuum_after_run=False,
        vacuum_retention_days=7,
        dry_run=False,
    )

    with pytest.raises(StorageError, match="vacuum failed"):
        await service.finalize_run(config, runtime)  # type: ignore[arg-type]
