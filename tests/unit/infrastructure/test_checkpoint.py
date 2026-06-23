"""Unit tests for local checkpointing."""

from __future__ import annotations

import json
from uuid import UUID

import pytest

from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter


@pytest.mark.unit
class TestLocalCheckpoint:
    """Test LocalCheckpointAdapter functionality."""

    def test_local_checkpoint_initialization(self, tmp_path):
        """Test LocalCheckpointAdapter can be initialized."""
        cp = LocalCheckpointAdapter(base_path=tmp_path)
        assert cp.base_path == tmp_path

    async def test_save_creates_file(self, tmp_path):
        """Test save creates checkpoint file.

        Flat structure: {base_path}/{pipeline}.json
        """
        cp = LocalCheckpointAdapter(base_path=tmp_path)

        pipeline = "test_pipeline"
        run_id = UUID("12345678-1234-5678-1234-567812345678")

        await cp.save(pipeline, run_id, {"key": "value"})

        # Flat structure: checkpoint file directly in base_path
        checkpoint_file = tmp_path / "test_pipeline.json"
        assert checkpoint_file.exists()

    async def test_load_returns_correct_data(self, tmp_path):
        """Test that load returns the correct data.

        Flat structure: {base_path}/{pipeline}.json
        """
        # Create checkpoint file (flat structure)
        checkpoint_file = tmp_path / "test_pipeline.json"
        checkpoint_file.write_text(
            json.dumps(
                {
                    "pipeline": "test_pipeline",
                    "run_id": "12345678-1234-5678-1234-567812345678",
                    "metadata": {"key": "value"},
                    "version": "2.0",
                }
            )
        )

        cp = LocalCheckpointAdapter(base_path=tmp_path)

        result = await cp.load("test_pipeline")

        assert result is not None
        run_id, metadata = result
        assert run_id == UUID("12345678-1234-5678-1234-567812345678")
        assert metadata["key"] == "value"
        assert isinstance(metadata["checkpoint_saved_at_epoch_seconds"], float)

    async def test_load_nonexistent_returns_none(self, tmp_path):
        """Test load returns None for nonexistent checkpoint."""
        cp = LocalCheckpointAdapter(base_path=tmp_path)

        result = await cp.load("nonexistent_pipeline")

        assert result is None

    async def test_save_and_load_roundtrip(self, tmp_path):
        """Test save and load roundtrip."""
        cp = LocalCheckpointAdapter(base_path=tmp_path)

        pipeline = "test_pipeline"
        run_id = UUID("12345678-1234-5678-1234-567812345678")
        metadata = {"key": "value"}

        await cp.save(pipeline, run_id, metadata)
        result = await cp.load(pipeline)

        assert result is not None
        loaded_run_id, loaded_metadata = result
        assert loaded_run_id == run_id
        assert loaded_metadata["key"] == metadata["key"]
        assert isinstance(loaded_metadata["checkpoint_saved_at_epoch_seconds"], float)

    async def test_delete_removes_file__test_local_checkpoint_unit_infrastructure_test_checkpoint_89(
        self, tmp_path
    ):
        """Test delete removes checkpoint file.

        Flat structure: {base_path}/{pipeline}.json
        """
        # Create checkpoint file (flat structure)
        checkpoint_file = tmp_path / "test_pipeline.json"
        checkpoint_file.write_text(json.dumps({"pipeline": "test"}))

        cp = LocalCheckpointAdapter(base_path=tmp_path)

        await cp.delete("test_pipeline")

        assert not checkpoint_file.exists()

    async def test_delete_nonexistent_no_error(self, tmp_path):
        """Test delete doesn't raise error for nonexistent checkpoint."""
        cp = LocalCheckpointAdapter(base_path=tmp_path)

        # Should not raise
        await cp.delete("nonexistent_pipeline")

    async def test_exists_returns_true(self, tmp_path):
        """Test exists returns True for existing checkpoint.

        Flat structure: {base_path}/{pipeline}.json
        """
        # Create checkpoint file (flat structure)
        checkpoint_file = tmp_path / "test_pipeline.json"
        checkpoint_file.write_text("{}")

        cp = LocalCheckpointAdapter(base_path=tmp_path)

        result = await cp.exists("test_pipeline")

        assert result is True

    async def test_exists_returns_false(self, tmp_path):
        """Test exists returns False for nonexistent checkpoint."""
        cp = LocalCheckpointAdapter(base_path=tmp_path)

        result = await cp.exists("nonexistent_pipeline")

        assert result is False

    async def test_list_all_pipelines(self, tmp_path):
        """Test list_all returns all pipelines with checkpoints.

        Flat structure: {base_path}/{pipeline}.json
        """
        # Create checkpoint files (flat structure)
        for name in ["pipeline_a", "pipeline_b", "pipeline_c"]:
            checkpoint_file = tmp_path / f"{name}.json"
            checkpoint_file.write_text("{}")

        cp = LocalCheckpointAdapter(base_path=tmp_path)

        result = await cp.list_all()

        assert result == ["pipeline_a", "pipeline_b", "pipeline_c"]

    async def test_list_all_empty(self, tmp_path):
        """Test list_all returns empty list when no checkpoints."""
        cp = LocalCheckpointAdapter(base_path=tmp_path)

        result = await cp.list_all()

        assert result == []

    async def test_local_checkpoint__aclose__91c52df6(self, tmp_path):
        """Test aclose completes without error."""
        cp = LocalCheckpointAdapter(base_path=tmp_path)
        await cp.aclose()
        # Should complete without error

    async def test_atomic_write(self, tmp_path):
        """Test that writes are atomic (temp file + rename).

        Flat structure: {base_path}/{pipeline}.json
        """
        cp = LocalCheckpointAdapter(base_path=tmp_path)

        pipeline = "test_pipeline"
        run_id = UUID("12345678-1234-5678-1234-567812345678")

        # First save
        await cp.save(pipeline, run_id, {"version": 1})

        # Second save should overwrite atomically
        await cp.save(pipeline, run_id, {"version": 2})

        result = await cp.load(pipeline)
        assert result is not None
        _, metadata = result
        assert metadata["version"] == 2
        assert isinstance(metadata["checkpoint_saved_at_epoch_seconds"], float)

        # No temp files should remain (in base_path since it's flat structure)
        temp_files = list(tmp_path.glob(".checkpoint_*.tmp"))
        assert len(temp_files) == 0
