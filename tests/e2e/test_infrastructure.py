"""E2E tests for infrastructure components with Docker.

These tests verify that real infrastructure (MinIO, Redis) works correctly.
They do NOT test full pipeline execution, focusing instead on:
- Redis connectivity and locks
- MinIO bucket operations
- Service health checks
"""

import pytest


@pytest.mark.e2e
@pytest.mark.slow
async def test_redis_connection(e2e_redis_client):
    """Test that Redis is accessible and functional."""
    # Test basic operations
    await e2e_redis_client.set("test_key", "test_value")
    value = await e2e_redis_client.get("test_key")
    assert value == b"test_value"

    # Test deletion
    await e2e_redis_client.delete("test_key")
    value = await e2e_redis_client.get("test_key")
    assert value is None


@pytest.mark.e2e
@pytest.mark.slow
async def test_redis_locks(e2e_redis_client):
    """Test Redis distributed locking mechanism."""
    lock_key = "lock:test_pipeline"
    owner_id = "test_owner"

    # Acquire lock
    acquired = await e2e_redis_client.set(
        lock_key, owner_id, nx=True, ex=60
    )
    assert acquired is True, "Should acquire lock"

    # Try to acquire again (should fail)
    acquired_again = await e2e_redis_client.set(
        lock_key, "another_owner", nx=True, ex=60
    )
    assert acquired_again is None, "Should not acquire already locked resource"

    # Release lock
    await e2e_redis_client.delete(lock_key)

    # Should be able to acquire after release
    acquired_after_release = await e2e_redis_client.set(
        lock_key, owner_id, nx=True, ex=60
    )
    assert acquired_after_release is True, "Should acquire lock after release"

    # Cleanup
    await e2e_redis_client.delete(lock_key)


@pytest.mark.e2e
@pytest.mark.slow
def test_minio_bucket_operations(e2e_minio_client):
    """Test MinIO bucket operations."""
    # List buckets
    buckets = e2e_minio_client.list_buckets()
    bucket_names = [b["Name"] for b in buckets.get("Buckets", [])]

    # Verify required buckets exist
    required_buckets = ["bronze", "silver", "gold", "checkpoints"]
    for bucket in required_buckets:
        assert bucket in bucket_names, f"Bucket {bucket} should exist"


@pytest.mark.e2e
@pytest.mark.slow
def test_minio_object_operations(e2e_minio_client):
    """Test MinIO object upload/download."""
    bucket = "bronze"
    key = "test/e2e_test_object.txt"
    content = b"Hello from E2E test"

    # Upload object
    e2e_minio_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=content
    )

    # Download object
    response = e2e_minio_client.get_object(Bucket=bucket, Key=key)
    downloaded_content = response["Body"].read()
    assert downloaded_content == content

    # Delete object (cleanup)
    e2e_minio_client.delete_object(Bucket=bucket, Key=key)


@pytest.mark.e2e
@pytest.mark.slow
async def test_redis_lock_integration_with_bioetl(e2e_redis_client):
    """Test RedisDistributedLock with real Redis."""
    from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock

    lock = RedisDistributedLock(e2e_redis_client)
    lock_key = "chembl_activity"
    owner_id = "test_run_123"

    # Acquire lock
    acquired = await lock.acquire(lock_key, owner_id, ttl=60)
    assert acquired is True, "Should acquire lock"

    # Try to acquire with different owner (should fail)
    acquired_different = await lock.acquire(lock_key, "different_owner", ttl=60)
    assert acquired_different is False, "Should not acquire with different owner"

    # Release lock
    released = await lock.release(lock_key, owner_id)
    assert released is True, "Should release lock"

    # Verify lock is released
    acquired_after_release = await lock.acquire(lock_key, owner_id, ttl=60)
    assert acquired_after_release is True, "Should acquire lock after release"

    # Cleanup
    await lock.release(lock_key, owner_id)


@pytest.mark.e2e
@pytest.mark.slow
async def test_checkpoint_with_minio(e2e_minio_client):
    """Test S3Checkpoint with real MinIO."""
    from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
    from bioetl.domain.types import Watermark
    from uuid import uuid4

    checkpoint = S3Checkpoint(
        bucket="checkpoints",
        endpoint_url="http://localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
    )

    pipeline_name = "test_pipeline"
    run_id = uuid4()
    watermark = Watermark.from_id("e2e_test_watermark_123")
    checkpoint_data = {"last_processed_id": 12345, "batch_count": 10}

    # Save checkpoint
    await checkpoint.save(
        pipeline=pipeline_name, 
        run_id=run_id, 
        watermark=watermark, 
        metadata=checkpoint_data
    )

    # Load checkpoint
    loaded_data = await checkpoint.load(pipeline_name)
    assert loaded_data is not None
    loaded_watermark, loaded_run_id, loaded_metadata = loaded_data

    assert loaded_metadata == checkpoint_data, "Checkpoint metadata should match"
    assert loaded_run_id == run_id, "Run ID should match"
    assert loaded_watermark.to_api_param() == watermark.to_api_param(), "Checkpoint watermark should match"

    # Verify checkpoint file exists in MinIO
    # Note: the key for 'latest' is just the pipeline name
    key = f"checkpoints/{pipeline_name}/latest.json"
    response = e2e_minio_client.get_object(Bucket="checkpoints", Key=key)
    assert response is not None, "Checkpoint file should exist in MinIO"

    # Cleanup (optional)
    # e2e_minio_client.delete_object(Bucket="checkpoints", Key=key)
