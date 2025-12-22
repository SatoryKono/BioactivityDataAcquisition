"""End-to-end tests for ChEMBL Activity Pipeline.

Implements R16 - E2E tests with Docker.
Verifies the full pipeline flow using real Redis and MinIO instances.
"""

from uuid import uuid4

import pytest

from bioetl.composition.bootstrap import bootstrap_pipeline
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.domain.context import PipelineRunContext
from bioetl.domain.types import RunType


@pytest.fixture(autouse=True)
def ensure_registration():
    """Ensure pipeline factories are registered before E2E tests."""
    register_all_pipelines()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_chembl_pipeline_e2e(
    minio_service,
    redis_service,
    monkeypatch,
    tmp_path,
):
    """
    Test the full ChEMBL activity pipeline execution end-to-end.

    Setup:
    - Real Redis and MinIO (via docker-compose)
    - Configuration overrides for endpoints
    - Mocked ChEMBL API (using a small fake dataset to avoid network/time costs)

    Steps:
    1. Configure environment to point to Docker services.
    2. Bootstrap pipeline.
    3. Mock the fetcher to return controlled data.
    4. Run pipeline.
    5. Verify artifacts in MinIO (Bronze, Silver, Checkpoints).
    """

    # 1. Configuration Override
    run_id = uuid4()
    pipeline_name = "chembl_activity"

    # Override settings to use Docker services
    # Note: minio_service fixture provides http://localhost:<port>
    # AWSSettings defines aliases: bioetl_aws_endpoint_url, aws_endpoint_url
    monkeypatch.setenv("BIOETL_AWS_ENDPOINT_URL", minio_service)
    monkeypatch.setenv("BIOETL_AWS_ACCESS_KEY_ID", "minioadmin")
    monkeypatch.setenv("BIOETL_AWS_SECRET_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("BIOETL_AWS_REGION", "us-east-1")

    # Also set standard AWS env vars for libraries that might read them directly
    monkeypatch.setenv("AWS_ENDPOINT_URL", minio_service)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "minioadmin")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    # S3Settings uses BIOETL_S3__BUCKET_BRONZE (nested delimiter)
    monkeypatch.setenv("BIOETL_S3__BUCKET_BRONZE", "test-bronze")
    monkeypatch.setenv("BIOETL_S3__BUCKET_SILVER", "test-silver")
    monkeypatch.setenv("BIOETL_S3__BUCKET_GOLD", "test-gold")
    monkeypatch.setenv("BIOETL_S3__BUCKET_CHECKPOINTS", "test-checkpoints")
    monkeypatch.setenv("BIOETL_REDIS__HOST", "localhost")

    # Allow HTTP for Delta Lake (required for MinIO without SSL)
    monkeypatch.setenv("AWS_STORAGE_ALLOW_HTTP", "true")
    monkeypatch.setenv("AWS_S3_ALLOW_UNSAFE_RENAME", "true")
    # Force path-style addressing for MinIO
    monkeypatch.setenv("AWS_S3_ADDRESSING_STYLE", "path")
    # Disable S3 locking (not supported by MinIO out of the box)
    monkeypatch.setenv("AWS_S3_LOCKING_PROVIDER", "none")

    # Parse port from redis_service (redis://localhost:<port>)
    redis_port = redis_service.split(":")[-1]
    monkeypatch.setenv("BIOETL_REDIS__PORT", redis_port)

    # Ensure buckets exist
    import boto3

    s3 = boto3.client(
        "s3",
        endpoint_url=minio_service,
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
        region_name="us-east-1",
    )
    for bucket in ["test-bronze", "test-silver", "test-gold", "test-checkpoints"]:
        try:
            s3.create_bucket(Bucket=bucket)
        except Exception:
            pass  # Ignore if exists

    # 2. Bootstrap
    ctx = PipelineRunContext(
        pipeline_name=pipeline_name,
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        resume=False,
        limit=10,
    )
    runner = bootstrap_pipeline(ctx)

    # 3. Monkeypatch Data Source Fetch (avoid calling real ChEMBL API)
    # We want to test the PIPELINE logic (transform, write, lock, checkpoint),
    # not the ChEMBL API availability.

    async def mock_fetch(*args, **kwargs):
        # Yield 5 fake records
        records = [
            {
                "activity_id": 100 + i,
                "molecule_chembl_id": f"CHEMBL{i}",
                "target_chembl_id": "CHEMBL25",
                "standard_type": "IC50",
                "standard_value": float(i + 1),
                "standard_units": "nM",
                "pchembl_value": 5.0 + i * 0.5,  # Required by Gold schema
                "assay_chembl_id": "CHEMBL123",
                "document_chembl_id": "CHEMBL1",
            }
            for i in range(5)
        ]
        for record in records:
            yield record

    # Patch the fetch method of the data source adapter
    runner.services.data_source.fetch = mock_fetch

    # 4. Run Pipeline
    # runner.run() is the public entry point
    await runner.run()

    # 5. Verify Results

    # Verify Checkpoint is deleted after successful run (by design)
    # Checkpoints only persist if pipeline fails mid-execution for resume capability
    objs = s3.list_objects_v2(
        Bucket="test-checkpoints", Prefix=f"checkpoints/{pipeline_name}/"
    )
    assert (
        "Contents" not in objs or len(objs.get("Contents", [])) == 0
    ), "Checkpoint should be deleted after successful pipeline completion"

    # Verify Bronze
    objs = s3.list_objects_v2(Bucket="test-bronze", Prefix="bronze/v1/chembl/activity/")
    assert "Contents" in objs
    assert len(objs["Contents"]) > 0

    # Verify Silver (Delta Table)
    # Reading delta table from S3 in test might be tricky without configured storage options
    # Check if object exists at least
    objs = s3.list_objects_v2(Bucket="test-silver", Prefix="chembl_activity/")
    # Note: Delta Lake creates _delta_log/ and parquet files
    assert "Contents" in objs

    print("E2E Test Passed: Buckets populated and pipeline executed without error.")
