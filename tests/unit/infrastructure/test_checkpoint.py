"""Unit tests for checkpointing."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from botocore.exceptions import ClientError

from bioetl.domain.types import RunID, Watermark
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint


def make_sync_executor(loop: asyncio.AbstractEventLoop):
    """Create a run_in_executor replacement that returns awaitable sync results."""

    async def sync_executor(_, fn, *args):
        return fn(*args)

    return sync_executor


@pytest.fixture
def mock_s3_client():
    """Fixture for a mocked S3 client via S3ClientPool."""
    mock_s3 = MagicMock()
    with patch(
        "bioetl.infrastructure.storage.s3_pool.S3ClientPool.get_client"
    ) as mock_get_client:
        mock_get_client.return_value = mock_s3
        yield mock_s3


@pytest.mark.unit
class TestS3Checkpoint:
    """Test S3Checkpoint functionality."""

    @pytest.mark.usefixtures("mock_s3_client")
    def test_s3_checkpoint_initialization(self):
        """Test S3Checkpoint can be initialized."""
        cp = S3Checkpoint(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )
        assert cp.bucket == "test-bucket"

    async def test_save_generates_correct_key_and_body(self, mock_s3_client):
        """Test that save generates the correct S3 key and body."""
        # Mock head_object to return no existing checkpoint
        mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )

        cp = S3Checkpoint(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )
        # Inject the mock client
        cp.s3_client = mock_s3_client
        # Make run_in_executor execute synchronously for testing
        cp.loop = asyncio.get_event_loop()
        cp.loop.run_in_executor = make_sync_executor(cp.loop)

        pipeline = "test_pipeline"
        watermark: Watermark = datetime(2023, 1, 1, tzinfo=UTC)
        run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))
        metadata = {"key": "value"}

        await cp.save(pipeline, watermark, run_id, metadata)

        expected_key = "checkpoints/test_pipeline/latest.json"
        mock_s3_client.put_object.assert_called_once()
        _args, kwargs = mock_s3_client.put_object.call_args
        assert kwargs["Bucket"] == "test-bucket"
        assert kwargs["Key"] == expected_key
        # Body is a JSON string
        body = kwargs["Body"].decode("utf-8")
        assert "2023-01-01T00:00:00" in body
        assert "12345678-1234-5678-1234-567812345678" in body

    async def test_load_returns_correct_data(self, mock_s3_client):
        """Test that load returns the correct data."""
        cp = S3Checkpoint(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )
        # Inject the mock client
        cp.s3_client = mock_s3_client
        # Make run_in_executor execute synchronously for testing
        cp.loop = asyncio.get_event_loop()
        cp.loop.run_in_executor = make_sync_executor(cp.loop)

        pipeline = "test_pipeline"
        json_body = b'{"watermark": "2023-01-01T00:00:00+00:00", "run_id": "12345678-1234-5678-1234-567812345678", "metadata": {}}'
        mock_body = MagicMock()
        mock_body.read.return_value = json_body
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        result = await cp.load(pipeline)

        assert result is not None
        watermark, run_id, _metadata = result
        # Watermark is returned as a proper Watermark type
        assert isinstance(watermark, datetime)
        assert run_id == RunID(UUID("12345678-1234-5678-1234-567812345678"))

    async def test_load_nonexistent_checkpoint_returns_none(self, mock_s3_client):
        """Test that loading a nonexistent checkpoint returns None."""
        cp = S3Checkpoint(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )
        # Inject the mock client
        cp.s3_client = mock_s3_client
        # Make run_in_executor execute synchronously for testing
        cp.loop = asyncio.get_event_loop()
        cp.loop.run_in_executor = make_sync_executor(cp.loop)

        pipeline = "test_pipeline"
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )

        result = await cp.load(pipeline)

        assert result is None

    async def test_delete_calls_s3_delete_object(self, mock_s3_client):
        """Test that delete calls s3:deleteObject."""
        cp = S3Checkpoint(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )
        # Inject the mock client
        cp.s3_client = mock_s3_client
        # Make run_in_executor execute synchronously for testing
        cp.loop = asyncio.get_event_loop()
        cp.loop.run_in_executor = make_sync_executor(cp.loop)

        pipeline = "test_pipeline"

        await cp.delete(pipeline)

        expected_key = "checkpoints/test_pipeline/latest.json"
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key=expected_key
        )

    async def test_exists_returns_true(self, mock_s3_client):
        """Test that exists returns True when checkpoint exists."""
        cp = S3Checkpoint(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )
        cp.s3_client = mock_s3_client
        cp.loop = asyncio.get_event_loop()
        cp.loop.run_in_executor = make_sync_executor(cp.loop)

        # head_object succeeds = checkpoint exists
        mock_s3_client.head_object.return_value = {"ETag": '"abc123"'}

        result = await cp.exists("test_pipeline")

        assert result is True

    async def test_exists_returns_false(self, mock_s3_client):
        """Test that exists returns False when checkpoint doesn't exist."""
        cp = S3Checkpoint(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )
        cp.s3_client = mock_s3_client
        cp.loop = asyncio.get_event_loop()
        cp.loop.run_in_executor = make_sync_executor(cp.loop)

        mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "HeadObject"
        )

        result = await cp.exists("test_pipeline")

        assert result is False

    async def test_save_with_existing_etag(self, mock_s3_client):
        """Test that save uses If-Match when ETag exists."""
        cp = S3Checkpoint(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )
        cp.s3_client = mock_s3_client
        cp.loop = asyncio.get_event_loop()
        cp.loop.run_in_executor = make_sync_executor(cp.loop)

        # head_object returns existing ETag
        mock_s3_client.head_object.return_value = {"ETag": '"abc123"'}

        pipeline = "test_pipeline"
        watermark: Watermark = datetime(2023, 1, 1, tzinfo=UTC)
        run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))

        await cp.save(pipeline, watermark, run_id, {})

        # Should have called put_object with IfMatch
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]
        assert call_kwargs.get("IfMatch") == "abc123"

    async def test_aclose(self, mock_s3_client):
        """Test aclose completes without error."""
        cp = S3Checkpoint(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )
        await cp.aclose()
        # Should complete without error


@pytest.mark.unit
class TestS3CheckpointLocal:
    """Tests for S3Checkpoint in local mode."""

    async def test_save_local_creates_file(self, tmp_path):
        """Test save creates checkpoint file locally."""
        cp = S3Checkpoint(bucket=str(tmp_path))
        cp.loop = asyncio.get_event_loop()
        cp.loop.run_in_executor = make_sync_executor(cp.loop)

        pipeline = "test_pipeline"
        watermark: Watermark = datetime(2023, 1, 1, tzinfo=UTC)
        run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))

        await cp.save(pipeline, watermark, run_id, {"key": "value"})

        checkpoint_file = tmp_path / "checkpoints" / "test_pipeline" / "latest.json"
        assert checkpoint_file.exists()

    async def test_load_local_reads_file(self, tmp_path):
        """Test load reads checkpoint from local file."""
        import json

        # Create checkpoint file
        checkpoint_dir = tmp_path / "checkpoints" / "test_pipeline"
        checkpoint_dir.mkdir(parents=True)
        checkpoint_file = checkpoint_dir / "latest.json"
        checkpoint_file.write_text(json.dumps({
            "pipeline": "test_pipeline",
            "watermark": "2023-01-01T00:00:00+00:00",
            "run_id": "12345678-1234-5678-1234-567812345678",
            "metadata": {},
        }))

        cp = S3Checkpoint(bucket=str(tmp_path))
        cp.loop = asyncio.get_event_loop()
        cp.loop.run_in_executor = make_sync_executor(cp.loop)

        result = await cp.load("test_pipeline")

        assert result is not None
        watermark, run_id, _ = result
        assert isinstance(watermark, datetime)

    async def test_load_local_nonexistent_returns_none(self, tmp_path):
        """Test load returns None for nonexistent local checkpoint."""
        cp = S3Checkpoint(bucket=str(tmp_path))
        cp.loop = asyncio.get_event_loop()
        cp.loop.run_in_executor = make_sync_executor(cp.loop)

        result = await cp.load("nonexistent_pipeline")

        assert result is None

    async def test_delete_local_removes_file(self, tmp_path):
        """Test delete removes local checkpoint file."""
        import json

        # Create checkpoint file
        checkpoint_dir = tmp_path / "checkpoints" / "test_pipeline"
        checkpoint_dir.mkdir(parents=True)
        checkpoint_file = checkpoint_dir / "latest.json"
        checkpoint_file.write_text(json.dumps({"pipeline": "test"}))

        cp = S3Checkpoint(bucket=str(tmp_path))
        cp.loop = asyncio.get_event_loop()
        cp.loop.run_in_executor = make_sync_executor(cp.loop)

        await cp.delete("test_pipeline")

        assert not checkpoint_file.exists()

    async def test_exists_local_returns_true(self, tmp_path):
        """Test exists returns True for local checkpoint."""
        # Create checkpoint file
        checkpoint_dir = tmp_path / "checkpoints" / "test_pipeline"
        checkpoint_dir.mkdir(parents=True)
        checkpoint_file = checkpoint_dir / "latest.json"
        checkpoint_file.write_text("{}")

        cp = S3Checkpoint(bucket=str(tmp_path))
        cp.loop = asyncio.get_event_loop()
        cp.loop.run_in_executor = make_sync_executor(cp.loop)

        result = await cp.exists("test_pipeline")

        assert result is True

    async def test_exists_local_returns_false(self, tmp_path):
        """Test exists returns False for nonexistent local checkpoint."""
        cp = S3Checkpoint(bucket=str(tmp_path))
        cp.loop = asyncio.get_event_loop()
        cp.loop.run_in_executor = make_sync_executor(cp.loop)

        result = await cp.exists("nonexistent_pipeline")

        assert result is False
