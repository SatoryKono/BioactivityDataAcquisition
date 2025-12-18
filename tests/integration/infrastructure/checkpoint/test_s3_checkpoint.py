"""Integration tests for S3Checkpoint using moto."""

import uuid
from typing import AsyncGenerator

import boto3
import pytest
from botocore.config import Config
from moto import mock_aws

from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.domain.types import Watermark, RunID
from bioetl.infrastructure.storage.s3_pool import S3ClientPool

BUCKET_NAME = "test-checkpoints"
REGION = "us-east-1"


@pytest.fixture
def s3_client():
    """Create a mocked S3 client."""
    # Ensure S3ClientPool is cleared before and after to avoid using cached clients
    S3ClientPool.clear_pool()
    with mock_aws():
        client = boto3.client("s3", region_name=REGION)
        client.create_bucket(Bucket=BUCKET_NAME)
        yield client
    S3ClientPool.clear_pool()


@pytest.fixture
async def checkpoint(s3_client) -> AsyncGenerator[S3Checkpoint, None]:
    """Create an S3Checkpoint instance."""
    # Note: moto requires using the mocked environment, so we pass explicit None for creds/endpoint
    # to let boto3 find the mocked environment naturally, OR we can pass dummy creds.
    # S3Checkpoint uses run_in_executor with boto3.

    cp = S3Checkpoint(
        bucket=BUCKET_NAME,
        access_key="testing",
        secret_key="testing",
        region=REGION,
    )
    yield cp
    await cp.aclose()


@pytest.mark.asyncio
async def test_save_and_load_checkpoint(checkpoint):
    """Test saving and loading a checkpoint."""
    pipeline_name = f"test-pipeline-{uuid.uuid4()}"
    watermark = 12345
    run_id_val = uuid.uuid4()
    run_id = RunID(run_id_val)
    metadata = {"foo": "bar"}

    # Save
    await checkpoint.save(pipeline_name, watermark, run_id, metadata)

    # Load
    result = await checkpoint.load(pipeline_name)
    assert result is not None
    loaded_watermark, loaded_run_id, loaded_metadata = result

    assert loaded_watermark == watermark
    assert loaded_run_id == run_id_val # RunID is a NewType around UUID, so comparison with UUID works or it unwraps
    assert loaded_metadata == metadata


@pytest.mark.asyncio
async def test_load_nonexistent_checkpoint(checkpoint):
    """Test loading a checkpoint that does not exist."""
    pipeline_name = f"nonexistent-{uuid.uuid4()}"
    result = await checkpoint.load(pipeline_name)
    assert result is None


@pytest.mark.asyncio
async def test_list_all_checkpoints(checkpoint):
    """Test listing all checkpoints."""
    # Use unique prefix to avoid collision with other tests if bucket is shared or not cleaned properly
    prefix = str(uuid.uuid4())[:8]
    pipelines = [f"{prefix}_p1", f"{prefix}_p2", f"{prefix}_p3"]
    for p in pipelines:
        await checkpoint.save(p, 100, RunID(uuid.uuid4()), {})

    listed = await checkpoint.list_all()
    # Filter only our pipelines
    our_listed = [p for p in listed if p.startswith(prefix)]

    assert len(our_listed) == 3
    assert set(our_listed) == set(pipelines)


@pytest.mark.asyncio
async def test_delete_checkpoint(checkpoint):
    """Test deleting a checkpoint."""
    pipeline_name = "p-to-delete"
    await checkpoint.save(pipeline_name, 100, RunID(uuid.uuid4()), {})

    # Verify exists
    assert (await checkpoint.load(pipeline_name)) is not None

    # Delete
    await checkpoint.delete(pipeline_name)

    # Verify gone
    assert (await checkpoint.load(pipeline_name)) is None
