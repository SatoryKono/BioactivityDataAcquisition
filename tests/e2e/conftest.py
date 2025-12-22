"""Fixtures for E2E tests with real Docker infrastructure."""

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import boto3
    import redis.asyncio as aioredis


@pytest.fixture(scope="session", autouse=True)
def e2e_environment():
    """Set up environment for E2E tests."""
    # Set test environment variables
    os.environ["BIOETL_ENV"] = "dev"
    os.environ["BIOETL_TEST_MODE"] = "true"
    os.environ["BIOETL_S3_ENDPOINT"] = "http://localhost:9000"
    os.environ["BIOETL_S3_ACCESS_KEY"] = "minioadmin"
    os.environ["BIOETL_S3_SECRET_KEY"] = "minioadmin"
    os.environ["BIOETL_REDIS_URL"] = "redis://localhost:16379"

    yield

    # Cleanup settings cache after session
    try:
        from bioetl.infrastructure.config import get_settings

        get_settings.cache_clear()
    except ImportError:
        pass


@pytest.fixture
async def e2e_minio_client(minio_service) -> "boto3.client":
    """Create MinIO client and ensure buckets exist for E2E tests."""
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=minio_service,
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
    )

    # Create required buckets
    buckets = ["bronze", "silver", "gold", "checkpoints"]
    for bucket in buckets:
        try:
            client.create_bucket(Bucket=bucket)
        except client.exceptions.BucketAlreadyOwnedByYou:
            pass  # Bucket already exists
        except Exception as e:
            # In case of any other error, try to continue
            print(f"Warning: Could not create bucket {bucket}: {e}")

    yield client

    # Cleanup: Delete all objects and buckets (optional, for isolation)
    # Note: Commented out to avoid accidental data loss during development
    # for bucket in buckets:
    #     try:
    #         # Delete all objects in bucket
    #         response = client.list_objects_v2(Bucket=bucket)
    #         if "Contents" in response:
    #             for obj in response["Contents"]:
    #                 client.delete_object(Bucket=bucket, Key=obj["Key"])
    #         # Delete bucket
    #         client.delete_bucket(Bucket=bucket)
    #     except Exception:
    #         pass


@pytest.fixture
async def e2e_redis_client(redis_service) -> "aioredis.Redis":
    """Create Redis client for E2E tests with cleanup."""
    import redis.asyncio as aioredis

    client = aioredis.from_url(redis_service)

    # Ensure clean state
    await client.flushdb()

    yield client

    # Cleanup
    await client.flushdb()
    await client.aclose()


@pytest.fixture
def e2e_temp_storage(tmp_path: Path) -> dict[str, Path]:
    """Create temporary directories for E2E test storage.

    Returns:
        dict: Paths for bronze, silver, gold, and checkpoints
    """
    bronze_path = tmp_path / "bronze"
    silver_path = tmp_path / "silver"
    gold_path = tmp_path / "gold"
    checkpoints_path = tmp_path / "checkpoints"

    bronze_path.mkdir()
    silver_path.mkdir()
    gold_path.mkdir()
    checkpoints_path.mkdir()

    return {
        "bronze": bronze_path,
        "silver": silver_path,
        "gold": gold_path,
        "checkpoints": checkpoints_path,
    }


@pytest.fixture
async def e2e_cleanup_infrastructure(e2e_redis_client):
    """Ensure infrastructure state is cleaned between E2E tests."""
    # Pre-test cleanup
    await e2e_redis_client.flushdb()

    yield

    # Post-test cleanup
    await e2e_redis_client.flushdb()

    # Clear S3 client pool
    try:
        from bioetl.infrastructure.storage.s3_client_pool import S3ClientPool

        S3ClientPool.clear_pool()
    except ImportError:
        pass

    # Clear settings cache
    try:
        from bioetl.composition.mappers.config_mapper import get_pipeline_config
        from bioetl.infrastructure.config import get_settings

        get_settings.cache_clear()
        get_pipeline_config.cache_clear()
    except ImportError:
        pass


@pytest.fixture
def e2e_pipeline_limit() -> int:
    """Limit number of records for E2E tests to keep them fast."""
    return 10


@pytest.fixture
def e2e_vcr_disabled():
    """Ensure VCR is disabled for E2E tests (we want real HTTP calls)."""
    # E2E tests should make real HTTP calls, not use VCR cassettes
    # This fixture serves as a marker/documentation
    pass
