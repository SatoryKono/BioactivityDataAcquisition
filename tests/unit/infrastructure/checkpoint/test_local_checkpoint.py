"""Unit tests for LocalCheckpointAdapter.

Tests checkpoint save/load/delete/list/exists operations
using local filesystem storage with atomic writes.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from bioetl.domain.types import RunID
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter


@pytest.fixture
def checkpoint_dir(tmp_path: Path) -> Path:
    """Create a temporary checkpoint directory."""
    d = tmp_path / "checkpoints"
    d.mkdir()
    return d


@pytest.fixture
def checkpoint(checkpoint_dir: Path) -> LocalCheckpointAdapter:
    """Create a LocalCheckpointAdapter instance."""
    return LocalCheckpointAdapter(base_path=checkpoint_dir)


@pytest.fixture
def run_id() -> RunID:
    """Create a test RunID."""
    return RunID(uuid4())


class TestLocalCheckpointInit:
    """Tests for LocalCheckpointAdapter initialization."""

    def test_init_with_string_path(self, tmp_path: Path) -> None:
        """Should accept string path."""
        cp = LocalCheckpointAdapter(base_path=str(tmp_path))
        assert cp.base_path == tmp_path

    def test_init_with_path_object(self, tmp_path: Path) -> None:
        """Should accept Path object."""
        cp = LocalCheckpointAdapter(base_path=tmp_path)
        assert cp.base_path == tmp_path

    def test_init_with_pipeline_name(self, tmp_path: Path) -> None:
        """Should store pipeline_name."""
        cp = LocalCheckpointAdapter(base_path=tmp_path, pipeline_name="test_pipeline")
        assert cp.pipeline_name == "test_pipeline"

    def test_init_default_pipeline_name_is_none(self, tmp_path: Path) -> None:
        """Pipeline name should default to None."""
        cp = LocalCheckpointAdapter(base_path=tmp_path)
        assert cp.pipeline_name is None


class TestLocalCheckpointSaveLoad:
    """Tests for save and load operations."""

    @pytest.mark.asyncio
    async def test_save_creates_file(
        self, checkpoint: LocalCheckpointAdapter, run_id: RunID
    ) -> None:
        """Save should create a checkpoint file."""
        await checkpoint.save("chembl_activity", run_id)
        assert (checkpoint.base_path / "chembl_activity.json").exists()

    @pytest.mark.asyncio
    async def test_save_and_load_roundtrip(
        self, checkpoint: LocalCheckpointAdapter, run_id: RunID
    ) -> None:
        """Should be able to load a saved checkpoint."""
        metadata = {"offset": 100, "batch": 5}
        await checkpoint.save("chembl_activity", run_id, metadata)

        result = await checkpoint.load("chembl_activity")
        assert result is not None
        loaded_run_id, loaded_metadata = result
        assert loaded_run_id == run_id
        assert loaded_metadata["offset"] == 100
        assert loaded_metadata["batch"] == 5

    @pytest.mark.asyncio
    async def test_save_without_metadata(
        self, checkpoint: LocalCheckpointAdapter, run_id: RunID
    ) -> None:
        """Save without metadata should store empty dict."""
        await checkpoint.save("test_pipeline", run_id)
        result = await checkpoint.load("test_pipeline")
        assert result is not None
        _, loaded_metadata = result
        assert loaded_metadata == {}

    @pytest.mark.asyncio
    async def test_save_with_none_metadata(
        self, checkpoint: LocalCheckpointAdapter, run_id: RunID
    ) -> None:
        """Save with None metadata should store empty dict."""
        await checkpoint.save("test_pipeline", run_id, None)
        result = await checkpoint.load("test_pipeline")
        assert result is not None
        _, loaded_metadata = result
        assert loaded_metadata == {}

    @pytest.mark.asyncio
    async def test_load_nonexistent_returns_none(
        self, checkpoint: LocalCheckpointAdapter
    ) -> None:
        """Load for nonexistent pipeline should return None."""
        result = await checkpoint.load("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_save_overwrites_existing(
        self, checkpoint: LocalCheckpointAdapter
    ) -> None:
        """Save should overwrite existing checkpoint."""
        run_id1 = RunID(uuid4())
        run_id2 = RunID(uuid4())

        await checkpoint.save("pipeline", run_id1, {"v": 1})
        await checkpoint.save("pipeline", run_id2, {"v": 2})

        result = await checkpoint.load("pipeline")
        assert result is not None
        loaded_run_id, loaded_metadata = result
        assert loaded_run_id == run_id2
        assert loaded_metadata["v"] == 2

    @pytest.mark.asyncio
    async def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Save should create parent directories if missing."""
        deep_path = tmp_path / "a" / "b" / "c"
        cp = LocalCheckpointAdapter(base_path=deep_path)
        run_id = RunID(uuid4())
        await cp.save("test", run_id)
        assert (deep_path / "test.json").exists()

    @pytest.mark.asyncio
    async def test_save_persists_immutable_history_entry(
        self, checkpoint: LocalCheckpointAdapter, run_id: RunID
    ) -> None:
        """Save should preserve immutable per-run checkpoint evidence."""
        await checkpoint.save(
            "chembl_activity",
            run_id,
            {"manifest_id": "manifest-1", "offset": 100},
        )

        history_dir = (
            checkpoint.base_path
            / ".history"
            / "by_pipeline"
            / "chembl_activity"
            / str(run_id)
        )
        assert history_dir.exists()
        history_entries = sorted(history_dir.glob("*.json"))
        assert len(history_entries) == 1
        assert (
            checkpoint.base_path / ".history" / "by_manifest" / "manifest-1.json"
        ).exists()

    @pytest.mark.asyncio
    async def test_load_for_run_reads_latest_immutable_history_entry(
        self, checkpoint: LocalCheckpointAdapter
    ) -> None:
        """Run-scoped history loads should return the latest saved evidence."""
        run_id = RunID(uuid4())

        await checkpoint.save("pipeline", run_id, {"offset": 1})
        await checkpoint.save("pipeline", run_id, {"offset": 2})

        result = await checkpoint.load_for_run("pipeline", run_id)
        assert result is not None
        loaded_run_id, loaded_metadata = result
        assert loaded_run_id == run_id
        assert loaded_metadata["offset"] == 2

    @pytest.mark.asyncio
    async def test_load_for_manifest_id_uses_history_index(
        self, checkpoint: LocalCheckpointAdapter, run_id: RunID
    ) -> None:
        """Manifest lookup should resolve the immutable history entry."""
        await checkpoint.save(
            "pipeline",
            run_id,
            {"manifest_id": "manifest-lookup", "offset": 3},
        )

        result = await checkpoint.load_for_manifest_id("manifest-lookup")
        assert result is not None
        loaded_run_id, loaded_metadata = result
        assert loaded_run_id == run_id
        assert loaded_metadata["offset"] == 3


class TestLocalCheckpointDelete:
    """Tests for delete operation."""

    @pytest.mark.asyncio
    async def test_delete_removes_file(
        self, checkpoint: LocalCheckpointAdapter, run_id: RunID
    ) -> None:
        """Delete should remove checkpoint file."""
        await checkpoint.save("pipeline", run_id)
        assert (checkpoint.base_path / "pipeline.json").exists()

        await checkpoint.delete("pipeline")
        assert not (checkpoint.base_path / "pipeline.json").exists()

    @pytest.mark.asyncio
    async def test_delete_preserves_immutable_history(
        self, checkpoint: LocalCheckpointAdapter, run_id: RunID
    ) -> None:
        """Delete should only clear the mutable resume pointer."""
        await checkpoint.save(
            "pipeline",
            run_id,
            {"manifest_id": "manifest-delete", "offset": 1},
        )

        await checkpoint.delete("pipeline")

        result = await checkpoint.load_for_run("pipeline", run_id)
        assert result is not None
        loaded_run_id, loaded_metadata = result
        assert loaded_run_id == run_id
        assert loaded_metadata["offset"] == 1

    @pytest.mark.asyncio
    async def test_delete_nonexistent_is_noop(
        self, checkpoint: LocalCheckpointAdapter
    ) -> None:
        """Delete for nonexistent pipeline should not raise."""
        await checkpoint.delete("nonexistent")


class TestLocalCheckpointListAll:
    """Tests for list_all operation."""

    @pytest.mark.asyncio
    async def test_list_all_empty(self, checkpoint: LocalCheckpointAdapter) -> None:
        """Should return empty list when no checkpoints exist."""
        result = await checkpoint.list_all()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_all_multiple(self, checkpoint: LocalCheckpointAdapter) -> None:
        """Should list all pipelines with checkpoints."""
        for name in ["alpha", "beta", "gamma"]:
            await checkpoint.save(name, RunID(uuid4()))

        result = await checkpoint.list_all()
        assert result == ["alpha", "beta", "gamma"]

    @pytest.mark.asyncio
    async def test_list_all_sorted(self, checkpoint: LocalCheckpointAdapter) -> None:
        """Results should be sorted alphabetically."""
        for name in ["zebra", "alpha", "middle"]:
            await checkpoint.save(name, RunID(uuid4()))

        result = await checkpoint.list_all()
        assert result == ["alpha", "middle", "zebra"]

    @pytest.mark.asyncio
    async def test_list_all_nonexistent_base_path(self, tmp_path: Path) -> None:
        """Should return empty list when base path doesn't exist."""
        cp = LocalCheckpointAdapter(base_path=tmp_path / "nonexistent")
        result = await cp.list_all()
        assert result == []


class TestLocalCheckpointExists:
    """Tests for exists operation."""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, checkpoint: LocalCheckpointAdapter, run_id: RunID
    ) -> None:
        """Should return True for existing checkpoint."""
        await checkpoint.save("pipeline", run_id)
        assert await checkpoint.exists("pipeline") is True

    @pytest.mark.asyncio
    async def test_exists_false(self, checkpoint: LocalCheckpointAdapter) -> None:
        """Should return False for nonexistent checkpoint."""
        assert await checkpoint.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_exists_after_delete(
        self, checkpoint: LocalCheckpointAdapter, run_id: RunID
    ) -> None:
        """Should return False after deletion."""
        await checkpoint.save("pipeline", run_id)
        await checkpoint.delete("pipeline")
        assert await checkpoint.exists("pipeline") is False


class TestLocalCheckpointAclose:
    """Tests for aclose operation."""

    @pytest.mark.asyncio
    async def test_aclose_is_noop(self, checkpoint: LocalCheckpointAdapter) -> None:
        """aclose should not raise and be a no-op."""
        await checkpoint.aclose()


class TestLocalCheckpointGetKey:
    """Tests for _get_key internal method."""

    def test_get_key_format(self, checkpoint: LocalCheckpointAdapter) -> None:
        """Should return pipeline.json format."""
        assert checkpoint._get_key("chembl_activity") == "chembl_activity.json"
