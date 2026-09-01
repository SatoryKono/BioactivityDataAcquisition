# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Coverage boost tests for bronze_writer_io_mixin.py.

Targets uncovered lines: 78-79, 161, 192, 199, 266-274, 286-292.
"""

from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.storage.bronze.io_mixin import BronzeWriterIOMixin
from bioetl.infrastructure.storage.bronze import io_mixin


class _ConcreteBronzeMixin(BronzeWriterIOMixin):
    """Concrete subclass for testing BronzeWriterIOMixin."""

    COMPRESSION_LEVEL = 3
    COMPRESSION_THREADS = 1
    COMPRESSION_CHUNK_SIZE = 65536

    def __init__(self, base_path: Path, flat_structure: bool = False) -> None:
        self.base_path = base_path
        self._flat_structure = flat_structure
        self.logger = MagicMock()
        self._logger = self.logger
        self._metrics = MagicMock()
        self._resolve_bronze_path = lambda provider, entity, date_str, filename: (
            f"{date_str}/{filename}"
            if self._flat_structure
            else f"{provider}/{entity}/{date_str}/{filename}"
        )


@pytest.mark.integration
class TestWriteAtomicStreamEdgeCases:
    """Tests for _write_atomic_stream (lines 78-79)."""

    def test_write_atomic_stream_empty_buffer_flushes(self, tmp_path: Path) -> None:
        """Lines 78-79: chunk_buffer flushed at end if non-empty."""
        mixin = _ConcreteBronzeMixin(tmp_path)
        target = tmp_path / "test.jsonl.zst"

        # Records smaller than COMPRESSION_CHUNK_SIZE — will be in chunk_buffer at end
        records = [b'{"id": 1}\n', b'{"id": 2}\n']
        record_count, uncomp_size = mixin._write_atomic_stream(iter(records), target)

        assert target.exists()
        assert record_count == 2
        assert uncomp_size == sum(len(r) for r in records)

    def test_write_atomic_stream_no_records_raises(self, tmp_path: Path) -> None:
        """Line 84-86: no records raises ValueError."""
        mixin = _ConcreteBronzeMixin(tmp_path)
        target = tmp_path / "empty.jsonl.zst"

        with pytest.raises(ValueError, match="No records to write"):
            mixin._write_atomic_stream(iter([]), target)

        # Temp file should be cleaned up
        assert not target.exists()
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0


@pytest.mark.parametrize("existing", [b"same", b"different"])
def test_write_bytes_if_absent_or_same_handles_exclusive_create_race(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    existing: bytes,
) -> None:
    """A concurrent creator must be validated without overwriting its payload."""
    target = tmp_path / "race.bin"
    target.write_bytes(existing)

    def simulate_concurrent_publish(source: Path, final_target: Path) -> None:
        """
        Simulate a concurrent publication collision.

        Parameters:
                source (Path): Temporary source path for the simulated publication.
                final_target (Path): Target path reported as already published.

        Raises:
                FileExistsError: Always, using `final_target` as the conflicting path.
        """
        del source
        raise FileExistsError(final_target)

    monkeypatch.setattr(
        io_mixin,
        "_publish_new_file_exclusive",
        simulate_concurrent_publish,
    )

    if existing == b"same":
        io_mixin.write_bytes_if_absent_or_same(
            target, b"same", mismatch_message="mismatch"
        )
    else:
        with pytest.raises(FileExistsError, match="mismatch"):
            io_mixin.write_bytes_if_absent_or_same(
                target, b"same", mismatch_message="mismatch"
            )

    def test_write_atomic_stream_large_chunk_triggers_mid_write(
        self, tmp_path: Path
    ) -> None:
        """Lines 77-79: chunk_buffer exceeding COMPRESSION_CHUNK_SIZE triggers write."""
        mixin = _ConcreteBronzeMixin(tmp_path)
        mixin.COMPRESSION_CHUNK_SIZE = 10  # Very small to force flush
        target = tmp_path / "chunked.jsonl.zst"

        records = [b"x" * 15]  # Larger than chunk size
        count, _ = mixin._write_atomic_stream(iter(records), target)
        assert count == 1

    def test_write_atomic_stream_cleans_up_on_error(self, tmp_path: Path) -> None:
        """Lines 88-91: exception during write cleans up temp file."""
        mixin = _ConcreteBronzeMixin(tmp_path)
        target = tmp_path / "fail.jsonl.zst"

        def bad_records():
            yield b'{"id": 1}\n'
            raise RuntimeError("simulated error")

        with pytest.raises(RuntimeError):
            mixin._write_atomic_stream(bad_records(), target)

        assert not target.exists()
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0


@pytest.mark.integration
class TestListBatches:
    """Tests for list_batches (lines 160-182)."""

    @pytest.mark.asyncio
    async def test_list_batches_no_date_uses_glob_pattern(self, tmp_path: Path) -> None:
        """Line 173: no date uses '**/*.jsonl.zst' glob."""
        mixin = _ConcreteBronzeMixin(tmp_path)
        provider_path = tmp_path / "chembl" / "activity" / "2025-01-15"
        provider_path.mkdir(parents=True)
        (provider_path / "batch_2025-01-15_001.jsonl.zst").write_bytes(b"data")

        result = await mixin.list_batches("chembl", "activity")

        assert len(result) == 1
        assert "2025-01-15" in result[0]

    @pytest.mark.asyncio
    async def test_list_batches_with_date_uses_date_glob(self, tmp_path: Path) -> None:
        """Line 173: with date uses 'batch_*.jsonl.zst' pattern."""
        mixin = _ConcreteBronzeMixin(tmp_path)
        date = datetime(2025, 1, 15, tzinfo=UTC)
        date_path = tmp_path / "chembl" / "activity" / "2025-01-15"
        date_path.mkdir(parents=True)
        (date_path / "batch_2025-01-15_001.jsonl.zst").write_bytes(b"data")
        (date_path / "batch_2025-01-15_002.jsonl.zst").write_bytes(b"data2")

        result = await mixin.list_batches("chembl", "activity", date=date)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_batches_missing_path_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """Line 170-171: nonexistent path returns empty list."""
        mixin = _ConcreteBronzeMixin(tmp_path)

        result = await mixin.list_batches("nonexistent", "entity")

        assert result == []

    @pytest.mark.asyncio
    async def test_list_batches_flat_structure_no_provider(
        self, tmp_path: Path
    ) -> None:
        """Line 161: flat_structure with empty provider/entity."""
        mixin = _ConcreteBronzeMixin(tmp_path, flat_structure=True)
        date = datetime(2025, 1, 15, tzinfo=UTC)
        date_path = tmp_path / "2025-01-15"
        date_path.mkdir(parents=True)
        (date_path / "batch_2025-01-15_001.jsonl.zst").write_bytes(b"data")

        result = await mixin.list_batches("", "", date=date)
        # flat_structure + date: searches tmp_path / "2025-01-15"
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_batches_sorted_result(self, tmp_path: Path) -> None:
        """Lines 174-175: results are sorted."""
        mixin = _ConcreteBronzeMixin(tmp_path)
        path = tmp_path / "chembl" / "activity" / "2025-01-15"
        path.mkdir(parents=True)
        (path / "batch_2025-01-15_002.jsonl.zst").write_bytes(b"data2")
        (path / "batch_2025-01-15_001.jsonl.zst").write_bytes(b"data1")

        result = await mixin.list_batches("chembl", "activity")

        assert result == sorted(result)


@pytest.mark.integration
class TestFindOldDateDirs:
    """Tests for _find_old_date_dirs (line 192)."""

    def test_nonexistent_base_path_returns_empty(self, tmp_path: Path) -> None:
        """Line 192: missing base_path returns []."""
        mixin = _ConcreteBronzeMixin(tmp_path / "nonexistent")

        result = mixin._find_old_date_dirs("2025-01-01")

        assert result == []

    def test_returns_old_date_dirs(self, tmp_path: Path) -> None:
        """Lines 194-205: finds date dirs older than cutoff."""
        mixin = _ConcreteBronzeMixin(tmp_path)

        old_dir = tmp_path / "chembl" / "activity" / "2024-12-01"
        old_dir.mkdir(parents=True)
        new_dir = tmp_path / "chembl" / "activity" / "2025-02-01"
        new_dir.mkdir(parents=True)

        result = mixin._find_old_date_dirs("2025-01-01")

        assert old_dir in result
        assert new_dir not in result

    def test_provider_entity_filter(self, tmp_path: Path) -> None:
        """Lines 194-195: glob pattern uses provider/entity."""
        mixin = _ConcreteBronzeMixin(tmp_path)

        old_chembl = tmp_path / "chembl" / "activity" / "2024-12-01"
        old_chembl.mkdir(parents=True)
        old_pubchem = tmp_path / "pubchem" / "compound" / "2024-12-01"
        old_pubchem.mkdir(parents=True)

        result = mixin._find_old_date_dirs("2025-01-01", provider="chembl")

        assert old_chembl in result
        # pubchem dir with chembl filter should not appear if filter is specific
        assert old_pubchem not in result

    def test_is_old_date_dir_true_for_older(self, tmp_path: Path) -> None:
        """_is_old_date_dir returns True for date < cutoff."""
        mixin = _ConcreteBronzeMixin(tmp_path)
        old = tmp_path / "2024-12-01"
        old.mkdir()

        assert mixin._is_old_date_dir(old, "2025-01-01") is True

    def test_is_old_date_dir_false_for_newer(self, tmp_path: Path) -> None:
        """_is_old_date_dir returns False for date >= cutoff."""
        mixin = _ConcreteBronzeMixin(tmp_path)
        new = tmp_path / "2025-02-01"
        new.mkdir()

        assert mixin._is_old_date_dir(new, "2025-01-01") is False

    def test_is_old_date_dir_false_for_non_date_dir(self, tmp_path: Path) -> None:
        """_is_old_date_dir returns False for non-date-named dir."""
        mixin = _ConcreteBronzeMixin(tmp_path)
        non_date = tmp_path / "_delta_log"
        non_date.mkdir()

        assert mixin._is_old_date_dir(non_date, "2025-01-01") is False


@pytest.mark.integration
class TestCleanupOldFiles:
    """Tests for cleanup_old_files (lines 266-274)."""

    @pytest.mark.asyncio
    async def test_cleanup_dry_run_does_not_delete(self, tmp_path: Path) -> None:
        """Line 199: dry_run=True counts files without deleting."""
        mixin = _ConcreteBronzeMixin(tmp_path)

        old_dir = tmp_path / "chembl" / "activity" / "2024-12-01"
        old_dir.mkdir(parents=True)
        (old_dir / "batch.jsonl.zst").write_bytes(b"data")

        cutoff = datetime(2025, 1, 1, tzinfo=UTC)
        result = await mixin.cleanup_old_files(cutoff, dry_run=True)

        # File still exists
        assert (old_dir / "batch.jsonl.zst").exists()
        assert result["files_removed"] == 1
        assert result["bytes_freed"] > 0

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_files(self, tmp_path: Path) -> None:
        """Lines 227-232: non-dry run removes files and dirs."""
        mixin = _ConcreteBronzeMixin(tmp_path)

        old_dir = tmp_path / "chembl" / "activity" / "2024-12-01"
        old_dir.mkdir(parents=True)
        (old_dir / "batch1.jsonl.zst").write_bytes(b"data1")
        (old_dir / "batch2.jsonl.zst").write_bytes(b"data2")

        cutoff = datetime(2025, 1, 1, tzinfo=UTC)
        result = await mixin.cleanup_old_files(cutoff, dry_run=False)

        assert result["files_removed"] == 2
        assert not (old_dir / "batch1.jsonl.zst").exists()

    @pytest.mark.asyncio
    async def test_cleanup_increments_metrics(self, tmp_path: Path) -> None:
        """Lines 243-250: metrics incremented when files removed."""
        mixin = _ConcreteBronzeMixin(tmp_path)
        metrics = MagicMock()
        mixin._metrics = metrics

        old_dir = tmp_path / "chembl" / "activity" / "2024-12-01"
        old_dir.mkdir(parents=True)
        (old_dir / "batch.jsonl.zst").write_bytes(b"data")

        cutoff = datetime(2025, 1, 1, tzinfo=UTC)
        await mixin.cleanup_old_files(cutoff, dry_run=False)

        assert metrics.increment_counter.call_count >= 2

    @pytest.mark.asyncio
    async def test_cleanup_no_old_files_no_metrics(self, tmp_path: Path) -> None:
        """Line 242: no files removed = no metrics increment."""
        mixin = _ConcreteBronzeMixin(tmp_path)
        metrics = MagicMock()
        mixin._metrics = metrics

        # No old files exist
        cutoff = datetime(2020, 1, 1, tzinfo=UTC)
        result = await mixin.cleanup_old_files(cutoff, dry_run=False)

        assert result["files_removed"] == 0
        metrics.increment_counter.assert_not_called()


@pytest.mark.integration
class TestPreviewCleanupBronze:
    """Tests for preview_cleanup (lines 286-292)."""

    def test_preview_cleanup_with_provider_entity(self, tmp_path: Path) -> None:
        """Lines 288-289: provider+entity resolves specific path."""
        mixin = _ConcreteBronzeMixin(tmp_path)
        provider_path = tmp_path / "chembl" / "activity"
        provider_path.mkdir(parents=True)
        (provider_path / "2025-01-15").mkdir()
        (provider_path / "2025-01-15" / "batch.jsonl.zst").write_bytes(b"data")

        result = mixin.preview_cleanup(provider="chembl", entity="activity")

        assert result["exists"] is True
        assert result["file_count"] == 1

    def test_preview_cleanup_with_provider_only(self, tmp_path: Path) -> None:
        """Line 290-291: provider only resolves to provider-level path."""
        mixin = _ConcreteBronzeMixin(tmp_path)
        provider_path = tmp_path / "chembl"
        provider_path.mkdir(parents=True)

        result = mixin.preview_cleanup(provider="chembl")

        assert result["path"] == str(provider_path)

    def test_preview_cleanup_base_path_fallback(self, tmp_path: Path) -> None:
        """Line 292: no provider/entity returns base_path."""
        mixin = _ConcreteBronzeMixin(tmp_path)

        result = mixin.preview_cleanup()

        assert result["path"] == str(tmp_path)

    def test_preview_cleanup_flat_structure_returns_base(self, tmp_path: Path) -> None:
        """Line 287: flat_structure=True returns base_path."""
        mixin = _ConcreteBronzeMixin(tmp_path, flat_structure=True)

        result = mixin.preview_cleanup(provider="chembl", entity="activity")

        assert result["path"] == str(tmp_path)

    def test_preview_cleanup_nonexistent_returns_zero_files(
        self, tmp_path: Path
    ) -> None:
        """Lines 268-269: nonexistent path returns file_count=0."""
        mixin = _ConcreteBronzeMixin(tmp_path)

        result = mixin.preview_cleanup(provider="nonexistent", entity="entity")

        assert result["file_count"] == 0
        assert result["exists"] is False
