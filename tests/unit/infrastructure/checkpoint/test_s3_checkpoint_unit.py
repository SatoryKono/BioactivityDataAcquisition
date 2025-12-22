"""Unit tests for S3Checkpoint."""

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from botocore.exceptions import ClientError

from bioetl.domain.exceptions import CheckpointConflictError
from bioetl.domain.types import RunID, Watermark
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint


def make_sync_executor(loop: asyncio.AbstractEventLoop):
    """Create a run_in_executor replacement that returns awaitable sync results."""

    async def sync_executor(_, fn, *args):
        return fn(*args)

    return sync_executor


@pytest.fixture
def mock_s3_client():
    """Fixture for a mocked boto3 S3 client."""
    client = MagicMock()
    # Mock paginator for list_all
    paginator = MagicMock()
    client.get_paginator.return_value = paginator
    return client


@pytest.fixture
def checkpoint_store(mock_s3_client):
    """Fixture for S3Checkpoint."""
    with patch(
        "bioetl.infrastructure.storage.s3_pool.S3ClientPool.get_client"
    ) as mock_get_client:
        mock_get_client.return_value = mock_s3_client
        store = S3Checkpoint(
            bucket="test-bucket",
            endpoint_url="http://localhost:9000",
            access_key="test",
            secret_key="test",
        )
        store.s3_client = mock_s3_client

        # Patch loop.run_in_executor to run synchronously
        store.loop = asyncio.get_event_loop()
        store.loop.run_in_executor = make_sync_executor(store.loop)

        yield store


@pytest.mark.asyncio
async def test_save_new_checkpoint(checkpoint_store, mock_s3_client):
    """Test saving a new checkpoint."""
    # Mock head_object to return 404 (not exists) for ETag check
    mock_s3_client.head_object.side_effect = ClientError(
        {"Error": {"Code": "404"}}, "HeadObject"
    )

    run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))
    watermark = Watermark.from_offset(100)
    await checkpoint_store.save("pipeline1", watermark, run_id)

    mock_s3_client.put_object.assert_called_once()
    _args, kwargs = mock_s3_client.put_object.call_args
    assert kwargs["Bucket"] == "test-bucket"
    assert kwargs["Key"] == "checkpoints/pipeline1/latest.json"
    assert "IfMatch" not in kwargs


@pytest.mark.asyncio
async def test_save_existing_checkpoint_with_etag(checkpoint_store, mock_s3_client):
    """Test saving over existing checkpoint using ETag."""
    # Mock head_object to return ETag
    mock_s3_client.head_object.side_effect = None
    mock_s3_client.head_object.return_value = {"ETag": '"current-etag"'}

    run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))
    watermark = Watermark.from_offset(100)
    await checkpoint_store.save("pipeline1", watermark, run_id)

    mock_s3_client.put_object.assert_called_once()
    _args, kwargs = mock_s3_client.put_object.call_args
    assert kwargs["IfMatch"] == "current-etag"


@pytest.mark.asyncio
async def test_save_conflict(checkpoint_store, mock_s3_client):
    """Test saving raises conflict error if ETag mismatch."""
    # First call to head_object gets ETag
    mock_s3_client.head_object.return_value = {"ETag": '"old-etag"'}

    # put_object raises PreconditionFailed
    mock_s3_client.put_object.side_effect = ClientError(
        {"Error": {"Code": "PreconditionFailed"}}, "PutObject"
    )

    run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))
    watermark = Watermark.from_offset(100)

    with pytest.raises(CheckpointConflictError):
        await checkpoint_store.save("pipeline1", watermark, run_id)


@pytest.mark.asyncio
async def test_load_exists(checkpoint_store, mock_s3_client):
    """Test loading an existing checkpoint."""
    mock_response = MagicMock()
    mock_response["Body"].read.return_value = (
        b'{"pipeline": "p1", "watermark": "100", "run_id": "12345678-1234-5678-1234-567812345678", "metadata": {"a": 1}}'
    )
    mock_s3_client.get_object.return_value = mock_response

    result = await checkpoint_store.load("pipeline1")

    assert result is not None
    watermark, run_id, metadata = result
    assert isinstance(watermark, Watermark)
    assert watermark.value == 100
    assert str(run_id) == "12345678-1234-5678-1234-567812345678"
    assert metadata == {"a": 1}


@pytest.mark.asyncio
async def test_load_not_exists(checkpoint_store, mock_s3_client):
    """Test loading a non-existent checkpoint."""
    mock_s3_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey"}}, "GetObject"
    )

    result = await checkpoint_store.load("pipeline1")
    assert result is None


@pytest.mark.asyncio
async def test_delete(checkpoint_store, mock_s3_client):
    """Test deleting a checkpoint."""
    await checkpoint_store.delete("pipeline1")
    mock_s3_client.delete_object.assert_called_once_with(
        Bucket="test-bucket", Key="checkpoints/pipeline1/latest.json"
    )


@pytest.mark.asyncio
async def test_delete_not_found_ignored(checkpoint_store, mock_s3_client):
    """Test deleting non-existent checkpoint does not raise."""
    mock_s3_client.delete_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey"}}, "DeleteObject"
    )
    await checkpoint_store.delete("pipeline1")  # Should not raise


@pytest.mark.asyncio
async def test_list_all(checkpoint_store, mock_s3_client):
    """Test listing all checkpoints."""
    paginator = mock_s3_client.get_paginator.return_value
    paginator.paginate.return_value = [
        {
            "CommonPrefixes": [
                {"Prefix": "checkpoints/pipeline1/"},
                {"Prefix": "checkpoints/pipeline2/"},
            ]
        },
        {"CommonPrefixes": [{"Prefix": "checkpoints/pipeline3/"}]},
    ]

    pipelines = await checkpoint_store.list_all()
    assert pipelines == ["pipeline1", "pipeline2", "pipeline3"]


@pytest.mark.asyncio
async def test_exists_true(checkpoint_store, mock_s3_client):
    """Test exists returns True."""
    mock_s3_client.head_object.return_value = {}
    assert await checkpoint_store.exists("pipeline1") is True


@pytest.mark.asyncio
async def test_exists_false(checkpoint_store, mock_s3_client):
    """Test exists returns False."""
    mock_s3_client.head_object.side_effect = ClientError(
        {"Error": {"Code": "404"}}, "HeadObject"
    )
    assert await checkpoint_store.exists("pipeline1") is False


@pytest.mark.unit
class TestS3CheckpointLocal:
    """Tests for S3Checkpoint in local mode."""

    def test_local_init(self):
        store = S3Checkpoint(bucket="/tmp")
        assert store.is_local

    async def test_local_save_load_delete(self, tmp_path):
        store = S3Checkpoint(bucket=str(tmp_path))
        run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))

        # Save
        watermark = Watermark.from_id("2024-01-01")
        await store.save("p1", watermark, run_id)
        assert (tmp_path / "checkpoints/p1/latest.json").exists()

        # Load
        watermark, loaded_run_id, _ = await store.load("p1")
        # 2024-01-01 could be parsed as date if ISO format
        # But here we saved "2024-01-01" as string/ID if passed as ID.
        # Wait, from_id("2024-01-01") -> value="2024-01-01".
        # to_api_param -> "2024-01-01".
        # load -> "2024-01-01" -> datetime.fromisoformat works!
        assert isinstance(watermark, Watermark)
        assert watermark.value == datetime(2024, 1, 1, 0, 0)
        assert loaded_run_id == run_id

        # List
        pipelines = await store.list_all()
        # Expect "p1" because local listing just returns directory names
        assert pipelines == ["p1"]

        # Exists
        assert await store.exists("p1")

        # Delete
        await store.delete("p1")
        assert not (tmp_path / "checkpoints/p1/latest.json").exists()
