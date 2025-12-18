import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from unittest.mock import MagicMock

try:
    import boto3
    from moto import mock_aws
    from botocore.exceptions import ClientError
    MOTO_AVAILABLE = True
except ImportError:
    MOTO_AVAILABLE = False

from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.storage.s3_pool import S3ClientPool
from bioetl.domain.types import RunID
from bioetl.domain.exceptions import CheckpointConflictError

pytestmark = pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto and boto3 are not installed")


BUCKET_NAME = "test-checkpoints"
# Use a valid AWS endpoint so moto intercepts it automatically
ENDPOINT_URL = "https://s3.us-east-1.amazonaws.com"

@pytest.fixture
def s3_mock():
    with mock_aws():
        # Clear pool to ensure we get a new client inside the mock context
        S3ClientPool.clear_pool()
        yield
        S3ClientPool.clear_pool()

@pytest.fixture
def s3_client(s3_mock):
    # Setup bucket
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket=BUCKET_NAME)
    return client

@pytest.fixture
def checkpoint_manager(s3_client):
    return S3Checkpoint(
        bucket=BUCKET_NAME,
        endpoint_url=ENDPOINT_URL,
        region="us-east-1",
        access_key="test",
        secret_key="test"
    )

@pytest.mark.asyncio
async def test_save_and_load_checkpoint(checkpoint_manager):
    pipeline = "test-pipeline"
    run_id = RunID(uuid4())
    watermark = datetime.now(timezone.utc)
    metadata = {"processed_records": 100}

    await checkpoint_manager.save(pipeline, watermark, run_id, metadata)

    result = await checkpoint_manager.load(pipeline)
    assert result is not None
    loaded_watermark, loaded_run_id, loaded_metadata = result

    # Datetime roundtrip via JSON might lose precision or change slightly depending on implementation
    # But isoformat() usually keeps it.
    assert loaded_watermark == watermark
    assert loaded_run_id == run_id
    assert loaded_metadata == metadata

@pytest.mark.asyncio
async def test_load_not_found(checkpoint_manager):
    result = await checkpoint_manager.load("non-existent")
    assert result is None

@pytest.mark.asyncio
async def test_exists(checkpoint_manager):
    pipeline = "test-exists"
    run_id = RunID(uuid4())
    watermark = datetime.now(timezone.utc)

    assert not await checkpoint_manager.exists(pipeline)

    await checkpoint_manager.save(pipeline, watermark, run_id)

    assert await checkpoint_manager.exists(pipeline)

@pytest.mark.asyncio
async def test_delete(checkpoint_manager):
    pipeline = "test-delete"
    run_id = RunID(uuid4())
    watermark = datetime.now(timezone.utc)

    await checkpoint_manager.save(pipeline, watermark, run_id)
    assert await checkpoint_manager.exists(pipeline)

    await checkpoint_manager.delete(pipeline)
    assert not await checkpoint_manager.exists(pipeline)

@pytest.mark.asyncio
async def test_list_all(checkpoint_manager):
    pipelines = ["p1", "p2", "p3"]
    run_id = RunID(uuid4())
    watermark = datetime.now(timezone.utc)

    for p in pipelines:
        await checkpoint_manager.save(p, watermark, run_id)

    result = await checkpoint_manager.list_all()
    assert result == sorted(pipelines)

@pytest.mark.asyncio
async def test_save_conflict(checkpoint_manager):
    """Test that CheckpointConflictError is raised when PreconditionFailed occurs."""
    pipeline = "test-conflict"
    run_id = RunID(uuid4())
    watermark = datetime.now(timezone.utc)

    # First save to establish initial state
    await checkpoint_manager.save(pipeline, watermark, run_id)

    # Mock the put_object method to raise ClientError with PreconditionFailed
    # We mock the underlying client's method
    original_put = checkpoint_manager.s3_client.put_object

    def side_effect(*args, **kwargs):
        error_response = {
            'Error': {
                'Code': 'PreconditionFailed',
                'Message': 'At least one of the pre-conditions you specified did not hold'
            }
        }
        raise ClientError(error_response, 'PutObject')

    checkpoint_manager.s3_client.put_object = MagicMock(side_effect=side_effect)

    try:
        with pytest.raises(CheckpointConflictError):
            await checkpoint_manager.save(pipeline, watermark, run_id)
    finally:
        # Restore method
        checkpoint_manager.s3_client.put_object = original_put
