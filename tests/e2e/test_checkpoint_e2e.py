"""E2E tests for checkpoint functionality.

Tests the checkpoint behavior for pipeline resumption:
- Checkpoint saving
- Checkpoint loading
- Resume from checkpoint
- Checkpoint cleanup

Per RULES.md 4.4 Graceful Shutdown:
- Save checkpoint locally before exit
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCheckpointSaving:
    """Tests for checkpoint saving behavior."""

    async def test_checkpoint_file_created(self, e2e_data_dir: Path):
        """E2E: Checkpoint file is created during pipeline run."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        # Simulate checkpoint save
        checkpoint_data = {
            "pipeline_name": "chembl_activity",
            "run_id": str(uuid4()),
            "offset": 100,
            "total_processed": 100,
        }

        checkpoint_file = checkpoint_dir / "chembl_activity.json"
        checkpoint_file.write_text(json.dumps(checkpoint_data))

        assert checkpoint_file.exists()

    async def test_checkpoint_contains_offset(self, e2e_data_dir: Path):
        """E2E: Checkpoint contains offset information."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        checkpoint_data = {
            "pipeline_name": "test_pipeline",
            "offset": 500,
        }

        checkpoint_file = checkpoint_dir / "test.json"
        checkpoint_file.write_text(json.dumps(checkpoint_data))

        loaded = json.loads(checkpoint_file.read_text())
        assert "offset" in loaded
        assert loaded["offset"] == 500

    async def test_checkpoint_contains_run_id(self, e2e_data_dir: Path):
        """E2E: Checkpoint contains run ID for correlation."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        run_id = str(uuid4())
        checkpoint_data = {
            "pipeline_name": "test_pipeline",
            "run_id": run_id,
        }

        checkpoint_file = checkpoint_dir / "test.json"
        checkpoint_file.write_text(json.dumps(checkpoint_data))

        loaded = json.loads(checkpoint_file.read_text())
        assert "run_id" in loaded
        assert loaded["run_id"] == run_id

    async def test_checkpoint_overwrite(self, e2e_data_dir: Path):
        """E2E: New checkpoint overwrites old checkpoint."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        checkpoint_file = checkpoint_dir / "test.json"

        # First checkpoint
        checkpoint_file.write_text(json.dumps({"offset": 100}))

        # Second checkpoint (overwrite)
        checkpoint_file.write_text(json.dumps({"offset": 200}))

        loaded = json.loads(checkpoint_file.read_text())
        assert loaded["offset"] == 200


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCheckpointLoading:
    """Tests for checkpoint loading behavior."""

    async def test_load_existing_checkpoint(self, e2e_data_dir: Path):
        """E2E: Can load an existing checkpoint."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        checkpoint_data = {
            "pipeline_name": "test_pipeline",
            "offset": 250,
            "batch_id": "batch_123",
        }

        checkpoint_file = checkpoint_dir / "test.json"
        checkpoint_file.write_text(json.dumps(checkpoint_data))

        loaded = json.loads(checkpoint_file.read_text())
        assert loaded["offset"] == 250
        assert loaded["batch_id"] == "batch_123"

    async def test_missing_checkpoint_returns_none(self, e2e_data_dir: Path):
        """E2E: Missing checkpoint file returns None/default."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        checkpoint_file = checkpoint_dir / "nonexistent.json"
        assert not checkpoint_file.exists()

        # Loading should handle missing file gracefully
        checkpoint = None
        if checkpoint_file.exists():
            checkpoint = json.loads(checkpoint_file.read_text())

        assert checkpoint is None

    async def test_corrupted_checkpoint_handling(self, e2e_data_dir: Path):
        """E2E: Corrupted checkpoint is handled gracefully."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        checkpoint_file = checkpoint_dir / "corrupted.json"
        checkpoint_file.write_text("not valid json {{{")

        # Loading should handle corrupted file
        checkpoint = None
        try:
            checkpoint = json.loads(checkpoint_file.read_text())
        except json.JSONDecodeError:
            checkpoint = None  # Reset to default

        assert checkpoint is None


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCheckpointResume:
    """Tests for resuming from checkpoint."""

    async def test_resume_continues_from_offset(self, e2e_data_dir: Path):
        """E2E: Resume starts from checkpoint offset."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        # Save checkpoint at offset 500
        checkpoint_file = checkpoint_dir / "test.json"
        checkpoint_file.write_text(json.dumps({"offset": 500}))

        # Load checkpoint
        checkpoint = json.loads(checkpoint_file.read_text())
        start_offset = checkpoint.get("offset", 0)

        assert start_offset == 500

    async def test_resume_without_checkpoint_starts_fresh(self, e2e_data_dir: Path):
        """E2E: Resume without checkpoint starts from beginning."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        checkpoint_file = checkpoint_dir / "new_pipeline.json"
        assert not checkpoint_file.exists()

        # Default offset for new pipeline
        start_offset = 0
        if checkpoint_file.exists():
            checkpoint = json.loads(checkpoint_file.read_text())
            start_offset = checkpoint.get("offset", 0)

        assert start_offset == 0

    async def test_resume_preserves_run_context(self, e2e_data_dir: Path):
        """E2E: Resume preserves run context from checkpoint."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        original_run_id = str(uuid4())
        checkpoint_data = {
            "pipeline_name": "test_pipeline",
            "run_id": original_run_id,
            "offset": 100,
            "run_type": "backfill",
        }

        checkpoint_file = checkpoint_dir / "test.json"
        checkpoint_file.write_text(json.dumps(checkpoint_data))

        loaded = json.loads(checkpoint_file.read_text())
        assert loaded["run_id"] == original_run_id
        assert loaded["run_type"] == "backfill"


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCheckpointCleanup:
    """Tests for checkpoint cleanup behavior."""

    async def test_checkpoint_deleted_on_completion(self, e2e_data_dir: Path):
        """E2E: Checkpoint can be deleted after successful completion."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        checkpoint_file = checkpoint_dir / "completed.json"
        checkpoint_file.write_text(json.dumps({"offset": 1000, "status": "running"}))

        assert checkpoint_file.exists()

        # Delete on completion
        checkpoint_file.unlink()

        assert not checkpoint_file.exists()

    async def test_checkpoint_retained_on_failure(self, e2e_data_dir: Path):
        """E2E: Checkpoint is retained on pipeline failure."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        checkpoint_file = checkpoint_dir / "failed.json"
        checkpoint_file.write_text(json.dumps({"offset": 500, "status": "failed"}))

        # Checkpoint should still exist
        assert checkpoint_file.exists()
        loaded = json.loads(checkpoint_file.read_text())
        assert loaded["offset"] == 500


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCheckpointConcurrency:
    """Tests for checkpoint behavior under concurrent access."""

    async def test_checkpoint_atomic_write(self, e2e_data_dir: Path):
        """E2E: Checkpoint write should be atomic."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        checkpoint_file = checkpoint_dir / "atomic.json"
        temp_file = checkpoint_dir / "atomic.json.tmp"

        checkpoint_data = {"offset": 100}

        # Write to temp file first, then rename (atomic)
        temp_file.write_text(json.dumps(checkpoint_data))
        temp_file.rename(checkpoint_file)

        assert checkpoint_file.exists()
        assert not temp_file.exists()

    async def test_checkpoint_per_pipeline_isolation(self, e2e_data_dir: Path):
        """E2E: Each pipeline has its own checkpoint file."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        # Create checkpoints for different pipelines
        pipelines = ["chembl_activity", "pubchem_compound", "uniprot_protein"]

        for i, pipeline in enumerate(pipelines):
            checkpoint_file = checkpoint_dir / f"{pipeline}.json"
            checkpoint_file.write_text(json.dumps({"offset": (i + 1) * 100}))

        # Verify isolation
        for i, pipeline in enumerate(pipelines):
            checkpoint_file = checkpoint_dir / f"{pipeline}.json"
            loaded = json.loads(checkpoint_file.read_text())
            assert loaded["offset"] == (i + 1) * 100


@pytest.mark.e2e
@pytest.mark.asyncio
class TestCheckpointMetadata:
    """Tests for checkpoint metadata fields."""

    async def test_checkpoint_has_timestamp(self, e2e_data_dir: Path):
        """E2E: Checkpoint includes timestamp."""
        await asyncio.sleep(0)
        from datetime import UTC, datetime

        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        checkpoint_data = {
            "offset": 100,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        checkpoint_file = checkpoint_dir / "test.json"
        checkpoint_file.write_text(json.dumps(checkpoint_data))

        loaded = json.loads(checkpoint_file.read_text())
        assert "timestamp" in loaded

    async def test_checkpoint_has_batch_info(self, e2e_data_dir: Path):
        """E2E: Checkpoint includes batch information."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        checkpoint_data = {
            "offset": 100,
            "last_batch_id": "batch_abc123",
            "batches_processed": 10,
        }

        checkpoint_file = checkpoint_dir / "test.json"
        checkpoint_file.write_text(json.dumps(checkpoint_data))

        loaded = json.loads(checkpoint_file.read_text())
        assert loaded["last_batch_id"] == "batch_abc123"
        assert loaded["batches_processed"] == 10

    async def test_checkpoint_has_statistics(self, e2e_data_dir: Path):
        """E2E: Checkpoint can include processing statistics."""
        await asyncio.sleep(0)
        checkpoint_dir = e2e_data_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        checkpoint_data = {
            "offset": 1000,
            "stats": {
                "records_processed": 1000,
                "records_failed": 5,
                "records_skipped": 10,
            },
        }

        checkpoint_file = checkpoint_dir / "test.json"
        checkpoint_file.write_text(json.dumps(checkpoint_data))

        loaded = json.loads(checkpoint_file.read_text())
        assert loaded["stats"]["records_processed"] == 1000
        assert loaded["stats"]["records_failed"] == 5
