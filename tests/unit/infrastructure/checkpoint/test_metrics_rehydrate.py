"""Checkpoint telemetry survives pointer cleanup without trusting corrupt history."""

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import UUID

import pytest

from bioetl.domain.types import RunID
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.infrastructure.checkpoint.metrics_rehydrate import (
    rehydrate_checkpoint_metrics,
)

NOW = datetime(2026, 9, 21, tzinfo=UTC)
SAVED = NOW.timestamp() - 86400 * 30


@pytest.mark.asyncio
async def test_restores_original_time_after_success_cleanup_and_restart(tmp_path):
    store = LocalCheckpointAdapter(tmp_path)
    await store.save(
        "chembl_assay",
        RunID(UUID(int=1)),
        {
            "checkpoint_saved_at_epoch_seconds": SAVED,
        },
    )
    await store.delete("chembl_assay")
    assert not await store.exists("chembl_assay")
    for _ in range(2):
        metrics = Mock()
        assert rehydrate_checkpoint_metrics(metrics, tmp_path, now=NOW) == 1
        metrics.set_gauge.assert_called_once_with(
            "bioetl_checkpoint_saved_at_seconds", SAVED, {"pipeline": "chembl_assay"}
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("timestamp", [None, 0, -1, True, "bad", NOW.timestamp() + 1])
async def test_invalid_timestamp_is_not_replaced_by_file_mtime(tmp_path, timestamp):
    await LocalCheckpointAdapter(tmp_path).save(
        "chembl_assay",
        RunID(UUID(int=1)),
        {"checkpoint_saved_at_epoch_seconds": timestamp},
    )
    metrics = Mock()
    assert rehydrate_checkpoint_metrics(metrics, tmp_path, now=NOW) == 0
    assert metrics.set_gauge.call_args.args[1] == 0


@pytest.mark.asyncio
async def test_corrupt_latest_evidence_does_not_fall_back(tmp_path):
    store = LocalCheckpointAdapter(tmp_path)
    await store.save(
        "chembl_assay",
        RunID(UUID(int=1)),
        {
            "checkpoint_saved_at_epoch_seconds": SAVED,
        },
    )
    # Corrupt the newer mutable pointer while valid history remains.
    (tmp_path / "chembl_assay.json").write_text('{"metadata": {}}')
    metrics = Mock()
    assert rehydrate_checkpoint_metrics(metrics, tmp_path, now=NOW) == 0
    assert metrics.set_gauge.call_args.args[1] == 0


@pytest.mark.unit
def test_missing_storage_does_not_invent_observation(tmp_path):
    metrics = Mock()
    assert rehydrate_checkpoint_metrics(metrics, tmp_path, now=NOW) == 0
    metrics.set_gauge.assert_not_called()
