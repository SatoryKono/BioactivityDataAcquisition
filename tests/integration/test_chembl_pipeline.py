"""Integration tests for the ChEMBL Activity pipeline."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline
from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.domain.pipeline_config import PipelineConfig
from bioetl.domain.types import RunType
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics


@pytest.mark.integration
async def test_chembl_pipeline_e2e(minio_service, redis_client):
    """
    End-to-end test for the ChEMBL Activity pipeline.

    This test verifies that the pipeline can be instantiated with real
    infrastructure components (MinIO, Redis) and validates the transform logic.
    """
    # 1. Create mock data source that yields test records
    mock_data_source = AsyncMock()
    mock_data_source.provider_name = "chembl"
    mock_data_source.aclose = AsyncMock()

    async def mock_fetch(*args, **kwargs):
        yield {
            "activity_id": 1,
            "molecule_chembl_id": "CHEMBL1",
            "target_chembl_id": "CHEMBL2",
            "assay_chembl_id": "CHEMBL3",
            "standard_type": "IC50",
            "standard_value": "10.0",
            "standard_units": "nM",
        }

    mock_data_source.fetch = mock_fetch

    # 2. Create pipeline configuration
    config = PipelineConfig(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type="activity",
        primary_keys=["activity_id"],
        silver_table="chembl.activity",
        gold_table="chembl.activity_gold",
        batch_size=100,
        checkpoint_interval=1000,
        fields=["activity_id", "molecule_chembl_id", "target_chembl_id", "standard_value"],
    )

    runtime = PipelineRuntimeConfig(
        run_type=RunType.INCREMENTAL,
        resume=False,
        limit=None,
    )

    # 3. Create mock storage (we're testing the pipeline, not storage)
    mock_storage = AsyncMock()
    mock_storage.write_bronze = AsyncMock()
    mock_storage.write_silver = AsyncMock()
    mock_storage.write_gold = AsyncMock()
    mock_storage.aclose = AsyncMock()

    # 4. Create real infrastructure components
    import structlog
    logger = structlog.get_logger()

    lock = RedisDistributedLock(redis_client)
    checkpoint = S3Checkpoint(
        bucket="checkpoints",
        endpoint_url=minio_service,
        access_key="minioadmin",
        secret_key="minioadmin",
    )

    # 5. Create pipeline services
    services = PipelineServices(
        data_source=mock_data_source,
        storage=mock_storage,
        lock=lock,
        checkpoint=checkpoint,
        quarantine=AsyncMock(),
        metrics=PrometheusMetrics(),
        logger=logger,
    )

    # 6. Create pipeline instance
    pipeline = ChEMBLActivityPipeline(config, runtime, services)

    # 7. Test transform method directly
    from bioetl.domain.context import PipelineContext

    context = PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=logger,
        pipeline_name="chembl_activity",
    )

    test_record = {
        "activity_id": 1,
        "molecule_chembl_id": "CHEMBL1",
        "target_chembl_id": "CHEMBL2",
        "assay_chembl_id": "CHEMBL3",
        "standard_type": "IC50",
        "standard_value": "10.0",
        "standard_units": "nM",
    }

    # Test transform_bronze_to_silver
    silver_record = await pipeline.transform_bronze_to_silver(context, test_record)
    assert silver_record is not None
    assert silver_record["activity_id"] == "1"
    assert silver_record["molecule_chembl_id"] == "CHEMBL1"
    assert silver_record["standard_value"] == 10.0


    # 8. Test should_write_gold
    assert pipeline.should_write_gold(context, silver_record) is True

    # Clean up
    await services.aclose()
