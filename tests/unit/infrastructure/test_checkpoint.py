"""Unit tests for local checkpointing."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from bioetl.domain.types import RunID, Watermark
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint


@pytest.mark.unit
class TestLocalCheckpoint:
    """Test LocalCheckpoint functionality."""

    def test_local_checkpoint_initialization(self, tmp_path):
        """Test LocalCheckpoint can be initialized."""
        cp = LocalCheckpoint(base_path=tmp_path)
        assert cp.base_path == tmp_path

    async def test_save_creates_file(self, tmp_path):
        """Test save creates checkpoint file."""
        cp = LocalCheckpoint(base_path=tmp_path)

        pipeline = "test_pipeline"
        watermark = Watermark.from_timestamp(datetime(2023, 1, 1, tzinfo=UTC))
        run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))

        await cp.save(pipeline, watermark, run_id, {"key": "value"})

        checkpoint_file = tmp_path / "checkpoints" / "test_pipeline" / "latest.json"
        assert checkpoint_file.exists()

    async def test_load_returns_correct_data(self, tmp_path):
        """Test that load returns the correct data."""
        import json

        # Create checkpoint file
        checkpoint_dir = tmp_path / "checkpoints" / "test_pipeline"
        checkpoint_dir.mkdir(parents=True)
        checkpoint_file = checkpoint_dir / "latest.json"
        checkpoint_file.write_text(
            json.dumps(
                {
                    "pipeline": "test_pipeline",
                    "watermark": "2023-01-01T00:00:00+00:00",
                    "run_id": "12345678-1234-5678-1234-567812345678",
                    "metadata": {"key": "value"},
                }
            )
        )

        cp = LocalCheckpoint(base_path=tmp_path)

        result = await cp.load("test_pipeline")

        assert result is not None
        watermark, run_id, metadata = result
        assert isinstance(watermark, Watermark)
        assert isinstance(watermark.value, datetime)
        assert run_id == RunID(UUID("12345678-1234-5678-1234-567812345678"))
        assert metadata == {"key": "value"}

    async def test_load_nonexistent_returns_none(self, tmp_path):
        """Test load returns None for nonexistent checkpoint."""
        cp = LocalCheckpoint(base_path=tmp_path)

        result = await cp.load("nonexistent_pipeline")

        assert result is None

    async def test_save_and_load_roundtrip(self, tmp_path):
        """Test save and load roundtrip."""
        cp = LocalCheckpoint(base_path=tmp_path)

        pipeline = "test_pipeline"
        watermark = Watermark.from_timestamp(datetime(2023, 1, 1, tzinfo=UTC))
        run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))
        metadata = {"key": "value"}

        await cp.save(pipeline, watermark, run_id, metadata)
        result = await cp.load(pipeline)

        assert result is not None
        loaded_watermark, loaded_run_id, loaded_metadata = result
        assert isinstance(loaded_watermark, Watermark)
        assert loaded_run_id == run_id
        assert loaded_metadata == metadata

    async def test_delete_removes_file(self, tmp_path):
        """Test delete removes checkpoint file."""
        import json

        # Create checkpoint file
        checkpoint_dir = tmp_path / "checkpoints" / "test_pipeline"
        checkpoint_dir.mkdir(parents=True)
        checkpoint_file = checkpoint_dir / "latest.json"
        checkpoint_file.write_text(json.dumps({"pipeline": "test"}))

        cp = LocalCheckpoint(base_path=tmp_path)

        await cp.delete("test_pipeline")

        assert not checkpoint_file.exists()

    async def test_delete_nonexistent_no_error(self, tmp_path):
        """Test delete doesn't raise error for nonexistent checkpoint."""
        cp = LocalCheckpoint(base_path=tmp_path)

        # Should not raise
        await cp.delete("nonexistent_pipeline")

    async def test_exists_returns_true(self, tmp_path):
        """Test exists returns True for existing checkpoint."""
        # Create checkpoint file
        checkpoint_dir = tmp_path / "checkpoints" / "test_pipeline"
        checkpoint_dir.mkdir(parents=True)
        checkpoint_file = checkpoint_dir / "latest.json"
        checkpoint_file.write_text("{}")

        cp = LocalCheckpoint(base_path=tmp_path)

        result = await cp.exists("test_pipeline")

        assert result is True

    async def test_exists_returns_false(self, tmp_path):
        """Test exists returns False for nonexistent checkpoint."""
        cp = LocalCheckpoint(base_path=tmp_path)

        result = await cp.exists("nonexistent_pipeline")

        assert result is False

    async def test_list_all_pipelines(self, tmp_path):
        """Test list_all returns all pipelines with checkpoints."""
        # Create checkpoint directories
        for name in ["pipeline_a", "pipeline_b", "pipeline_c"]:
            checkpoint_dir = tmp_path / "checkpoints" / name
            checkpoint_dir.mkdir(parents=True)
            (checkpoint_dir / "latest.json").write_text("{}")

        cp = LocalCheckpoint(base_path=tmp_path)

        result = await cp.list_all()

        assert result == ["pipeline_a", "pipeline_b", "pipeline_c"]

    async def test_list_all_empty(self, tmp_path):
        """Test list_all returns empty list when no checkpoints."""
        cp = LocalCheckpoint(base_path=tmp_path)

        result = await cp.list_all()

        assert result == []

    async def test_watermark_offset_roundtrip(self, tmp_path):
        """Test save/load with offset-based watermark."""
        cp = LocalCheckpoint(base_path=tmp_path)

        pipeline = "test_pipeline"
        watermark = Watermark.from_offset(12345)
        run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))

        await cp.save(pipeline, watermark, run_id, {})
        result = await cp.load(pipeline)

        assert result is not None
        loaded_watermark, _, _ = result
        assert isinstance(loaded_watermark.value, int)
        assert loaded_watermark.value == 12345

    async def test_watermark_id_roundtrip(self, tmp_path):
        """Test save/load with ID-based watermark."""
        cp = LocalCheckpoint(base_path=tmp_path)

        pipeline = "test_pipeline"
        watermark = Watermark.from_id("CHEMBL12345")
        run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))

        await cp.save(pipeline, watermark, run_id, {})
        result = await cp.load(pipeline)

        assert result is not None
        loaded_watermark, _, _ = result
        assert isinstance(loaded_watermark.value, str)
        assert loaded_watermark.value == "CHEMBL12345"

    async def test_aclose(self, tmp_path):
        """Test aclose completes without error."""
        cp = LocalCheckpoint(base_path=tmp_path)
        await cp.aclose()
        # Should complete without error

    async def test_atomic_write(self, tmp_path):
        """Test that writes are atomic (temp file + rename)."""
        cp = LocalCheckpoint(base_path=tmp_path)

        pipeline = "test_pipeline"
        watermark = Watermark.from_timestamp(datetime(2023, 1, 1, tzinfo=UTC))
        run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))

        # First save
        await cp.save(pipeline, watermark, run_id, {"version": 1})

        # Second save should overwrite atomically
        watermark2 = Watermark.from_timestamp(datetime(2023, 6, 1, tzinfo=UTC))
        await cp.save(pipeline, watermark2, run_id, {"version": 2})

        result = await cp.load(pipeline)
        assert result is not None
        _, _, metadata = result
        assert metadata == {"version": 2}

        # No temp files should remain
        checkpoint_dir = tmp_path / "checkpoints" / "test_pipeline"
        temp_files = list(checkpoint_dir.glob(".checkpoint_*.tmp"))
        assert len(temp_files) == 0
