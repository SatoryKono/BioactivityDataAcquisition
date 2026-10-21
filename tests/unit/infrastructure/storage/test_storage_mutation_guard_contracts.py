"""Cleanup and mutation failures retain ownership, accounting, and version guards."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pyarrow as pa
import pytest

from bioetl.infrastructure.storage import bronze_writer
from bioetl.infrastructure.storage.bronze import read_cleanup_mixin as cleanup
from bioetl.infrastructure.storage.silver import merge_resilience_helpers as merge
from bioetl.infrastructure.storage.silver.writer_metadata_facade import (
    SilverWriterMetadataFacade,
)
from bioetl.infrastructure.storage import (
    workflow_foreign_key_reconciliation_quarantine as reconciliation,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_silver_audit_normalizes_string_mode_for_metadata_operations():
    from bioetl.domain.medallion import SilverWriteMode

    writer = SilverWriterMetadataFacade()
    audit = AsyncMock()
    writer._metadata = SimpleNamespace(_log_silver_audit=audit)
    await writer._log_silver_audit(
        "table",
        [],
        "merge",
        run_id=None,
        run_type=None,
        source_batch_id=None,
        ingestion_ts=None,
    )
    assert audit.await_args.args[0].mode is SilverWriteMode.MERGE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "helper", [bronze_writer._drain_shielded_task, cleanup._drain_cleanup_worker]
)
async def test_cleanup_drain_waits_through_cancellation_until_worker_releases(helper):
    released = asyncio.Event()
    worker = asyncio.create_task(released.wait())
    drain = asyncio.create_task(helper(worker))
    await asyncio.sleep(0)
    drain.cancel()
    await asyncio.sleep(0)
    assert not worker.done()
    released.set()
    await drain
    assert worker.result() is True


@pytest.mark.asyncio
async def test_completed_io_error_remains_owned_by_original_task():
    error = OSError("write failed")

    async def fail():
        raise error

    worker = asyncio.create_task(fail())
    await asyncio.gather(worker, return_exceptions=True)
    await bronze_writer._wait_for_task_completion(worker)
    with pytest.raises(OSError) as caught:
        worker.result()
    assert caught.value is error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module, name",
    [
        (bronze_writer, "_drain_shielded_task"),
        (bronze_writer, "_wait_for_task_completion"),
        (cleanup, "_drain_cleanup_worker"),
    ],
)
async def test_shield_failure_before_worker_completion_is_not_suppressed(
    module, name, monkeypatch
):
    error = OSError("shield unavailable")
    worker = asyncio.get_running_loop().create_future()
    monkeypatch.setattr(
        module,
        "asyncio",
        SimpleNamespace(
            shield=AsyncMock(side_effect=error), CancelledError=asyncio.CancelledError
        ),
    )
    with pytest.raises(OSError) as caught:
        await getattr(module, name)(worker)
    assert caught.value is error and not worker.done()
    worker.cancel()


def test_invalid_configured_cleanup_identity_does_not_expand_the_scope():
    writer = cleanup.BronzeWriterReadCleanupMixin()
    writer._flat_structure = False
    writer._root_identity = ("..", "assay")
    assert writer._hierarchical_cleanup_scope(None, None) == (None, None)


@pytest.mark.parametrize(
    "reason, counter",
    [
        ("missing_scope", "directories_conflicted"),
        ("scan_error", "directories_failed"),
        ("unsupported", "directories_skipped"),
    ],
)
def test_cleanup_discovery_errors_retain_their_disposition(reason, counter):
    writer = cleanup.BronzeWriterReadCleanupMixin()
    writer._log_cleanup_skip = Mock()
    stats = {
        "directories_conflicted": 0,
        "directories_failed": 0,
        "directories_skipped": 0,
    }
    writer._record_cleanup_discovery_skip(stats, "path", reason)
    assert stats[counter] == 1 and sum(stats.values()) == 1


def test_rmdir_error_is_counted_without_claiming_directory_removal(
    tmp_path, monkeypatch
):
    writer = cleanup.BronzeWriterReadCleanupMixin()
    writer._log_cleanup_skip = Mock()
    monkeypatch.setattr(
        cleanup, "safe_rmdir", Mock(side_effect=OSError("directory in use"))
    )
    stats = {
        "directories_failed": 0,
        "directories_removed": 0,
        "directories_conflicted": 0,
    }
    plan = SimpleNamespace(path=tmp_path / "old", identity=object())
    writer._apply_planned_directory(stats, plan, tmp_path, tmp_path, None, Mock())
    assert stats == {
        "directories_failed": 1,
        "directories_removed": 0,
        "directories_conflicted": 0,
    }
    writer._log_cleanup_skip.assert_called_once_with(str(plan.path), "rmdir_error")


@pytest.mark.asyncio
async def test_partition_check_without_schema_evolution_preserves_request(monkeypatch):
    from bioetl.infrastructure.storage.silver.delta_request_models import (
        _DeltaWriteRequest,
    )
    from bioetl.domain.medallion import SilverWriteMode

    request = _DeltaWriteRequest(
        SilverWriteMode.MERGE, "table", pa.table({"id": [1]}), ["id"], ["id"]
    )
    monkeypatch.setattr(
        merge,
        "_load_delta_table",
        AsyncMock(
            return_value=SimpleNamespace(
                metadata=lambda: SimpleNamespace(partition_columns=["id"])
            )
        ),
    )
    result, evolved = await merge._pre_evolve_existing_table_schema(
        request=request, load_module=Mock()
    )
    assert result is request and evolved is False


@pytest.mark.asyncio
async def test_silver_audit_rejects_missing_metadata_operations():
    writer = SilverWriterMetadataFacade()
    with pytest.raises(RuntimeError, match="metadata operations are required"):
        await writer._log_silver_audit(
            "table",
            [],
            "append",
            run_id=None,
            run_type=None,
            source_batch_id=None,
            ingestion_ts=None,
        )


@pytest.mark.parametrize("layer", ["silver", "gold"])
def test_selected_snapshot_version_drift_blocks_mutation_before_merge(layer):
    table = SimpleNamespace(version=lambda: 2, merge=Mock())
    module = SimpleNamespace(DeltaTable=lambda path: table)
    with pytest.raises(ValueError, match="selected snapshot drift before"):
        if layer == "silver":
            reconciliation._delete_silver_orphan_rows_once(
                module, "table", [{"id": 1}], "id", 1
            )
        else:
            reconciliation._expire_gold_orphan_rows_once(
                module,
                "table",
                [{"id": 1}],
                "id",
                "valid_to",
                "is_current",
                reconciliation.GoldExpiryCommit("2026-10-21T00:00:00+00:00", 1),
            )
    table.merge.assert_not_called()
