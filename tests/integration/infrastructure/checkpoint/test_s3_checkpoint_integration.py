"""Integration tests for S3Checkpoint using moto.

Verifies that the S3Checkpoint class correctly interacts with an S3-compatible
storage system for saving, loading, deleting, and listing checkpoints.
"""
import asyncio
import pytest
import boto3
from uuid import uuid4
from datetime import datetime, timezone

from moto import mock_aws

from bioetl.domain.exceptions import CheckpointConflictError
from bioetl.domain.types import RunID, Watermark
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.storage.s3_pool import S3ClientPool

TEST_BUCKET = "test-checkpoints-bucket"
TEST_REGION = "us-east-1"


@pytest.fixture(scope="function")
def s3_client(monkeypatch):
    """Fixture to create a mocked S3 client and bucket."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", TEST_REGION)
    
    S3ClientPool.clear_pool()
    
    with mock_aws():
        import boto3
        client = boto3.client("s3", region_name=TEST_REGION)
        client.create_bucket(Bucket=TEST_BUCKET)
        yield client

    S3ClientPool.clear_pool()


@pytest.fixture
def checkpoint_storage(s3_client):
    """Fixture to create an S3Checkpoint instance configured for moto."""
    # Must provide an endpoint_url for S3Checkpoint to use S3 mode (not local file mode)
    # moto intercepts all boto3 calls so any URL works
    # However, to avoid connection errors when S3ClientPool tries to connect, we need
    # to be careful. Moto decorator patches boto3, but S3ClientPool might be creating a
    # session/client that bypasses or conflicts if not handled correctly.
    # We pass None as endpoint_url to rely on boto3's default behavior which moto patches.
    # But S3Checkpoint uses presence of endpoint_url to decide if it's local.
    # We'll use a valid-looking URL but rely on moto context.

    # IMPORTANT: Since we are using mock_aws context manager in the s3_client fixture,
    # any boto3 client created within that context (or while it's active) will be mocked.
    # S3Checkpoint uses S3ClientPool which creates a client.

    return S3Checkpoint(
        bucket=TEST_BUCKET,
        # We must provide endpoint_url to set is_local=False in S3Checkpoint.
        # Using a standard AWS URL ensures moto intercepts calls correctly.
        endpoint_url="https://s3.us-east-1.amazonaws.com",
        region=TEST_REGION,
        access_key="testing",
        secret_key="testing",
    )


@pytest.mark.asyncio
class TestS3Checkpoint:
    """Test suite for S3Checkpoint functionality."""

    async def test_save_and_load_checkpoint(self, checkpoint_storage: S3Checkpoint):
        """Verify that a checkpoint can be saved and then loaded correctly."""
        # Arrange
        pipeline_name = "test_pipeline_1"
        run_id = RunID(uuid4())
        watermark_ts = datetime.now(timezone.utc)
        watermark = Watermark.from_timestamp(watermark_ts)
        metadata = {"key": "value", "run_type": "incremental"}

        # Act
        await checkpoint_storage.save(pipeline_name, watermark, run_id, metadata)
        loaded_data = await checkpoint_storage.load(pipeline_name)

        # Assert
        assert loaded_data is not None
        loaded_watermark, loaded_run_id, loaded_metadata = loaded_data

        # Compare datetimes carefully (loaded_watermark is a Watermark object)
        assert isinstance(loaded_watermark, Watermark)
        assert loaded_watermark.value.replace(microsecond=0) == watermark_ts.replace(
            microsecond=0
        )
        assert loaded_run_id == run_id
        assert loaded_metadata == metadata

    async def test_load_non_existent_checkpoint(
        self, checkpoint_storage: S3Checkpoint
    ):
        """Verify that loading a non-existent checkpoint returns None."""
        # Arrange
        pipeline_name = "non_existent_pipeline"

        # Act
        loaded_data = await checkpoint_storage.load(pipeline_name)

        # Assert
        assert loaded_data is None

    async def test_delete_checkpoint(self, checkpoint_storage: S3Checkpoint):
        """Verify that a checkpoint can be deleted."""
        # Arrange
        pipeline_name = "test_pipeline_to_delete"
        run_id = RunID(uuid4())
        watermark = Watermark.from_offset(12345)

        await checkpoint_storage.save(pipeline_name, watermark, run_id, {})
        assert await checkpoint_storage.exists(pipeline_name) is True

        # Act
        await checkpoint_storage.delete(pipeline_name)

        # Assert
        assert await checkpoint_storage.exists(pipeline_name) is False
        assert await checkpoint_storage.load(pipeline_name) is None

    async def test_list_all_checkpoints(self, checkpoint_storage: S3Checkpoint):
        """Verify that list_all returns all pipelines with checkpoints."""
        # Arrange
        pipelines_to_create = ["pipeline_a", "pipeline_b", "pipeline_c"]
        for name in pipelines_to_create:
            await checkpoint_storage.save(name, Watermark.from_offset(1), RunID(uuid4()), {})

        # Act
        listed_pipelines = await checkpoint_storage.list_all()

        # Assert
        assert sorted(listed_pipelines) == sorted(pipelines_to_create)

    async def test_exists_method(self, checkpoint_storage: S3Checkpoint):
        """Verify the correctness of the exists() method."""
        # Arrange
        existing_pipeline = "existing_one"
        non_existing_pipeline = "non_existing_one"
        await checkpoint_storage.save(existing_pipeline, Watermark.from_offset(1), RunID(uuid4()), {})

        # Act & Assert
        assert await checkpoint_storage.exists(existing_pipeline) is True
        assert await checkpoint_storage.exists(non_existing_pipeline) is False

    async def test_atomic_save_conflict(
        self, checkpoint_storage: S3Checkpoint, s3_client
    ):
        """Verify that saving with a mismatched ETag raises CheckpointConflictError."""
        # Arrange
        pipeline_name = "conflict_pipeline"
        key = checkpoint_storage._get_key(pipeline_name)

        # Initial save to create an object with an ETag
        s3_client.put_object(
            Bucket=TEST_BUCKET, Key=key, Body='{"version": "0.1"}'
        )

        # Manually get the ETag to simulate a race condition
        # In a real scenario, another process would have changed the object
        # between our _get_etag and put_object calls.
        # Here, we simulate it by getting the ETag, changing the object,
        # and then trying to save, which will use the old (now invalid) ETag.
        old_etag = await checkpoint_storage._get_etag(key)
        assert old_etag is not None

        # Another process writes to the object, changing the ETag
        s3_client.put_object(
            Bucket=TEST_BUCKET, Key=key, Body='{"version": "0.2"}'
        )

        # Monkey-patch _get_etag to return the stale ETag for this one call
        original_get_etag = checkpoint_storage._get_etag

        async def mock_get_etag(k):
            return old_etag

        checkpoint_storage._get_etag = mock_get_etag

        # Act & Assert
        with pytest.raises(CheckpointConflictError):
            await checkpoint_storage.save(pipeline_name, Watermark.from_offset(123), RunID(uuid4()), {})

        # Restore original method
        checkpoint_storage._get_etag = original_get_etag
