"""Integration tests for the ChEMBL Activity pipeline."""
from unittest.mock import AsyncMock

import pytest

from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline
from bioetl.domain.types import RunType
from bioetl.infrastructure.checkpoint.s3_checkpoint import S3Checkpoint
from bioetl.infrastructure.locking.redis_lock import RedisDistributedLock
from tests.integration.memory_storage import MemoryStorage


class AsyncIterator:
    def __init__(self, data):
        self.data = data

    async def __aiter__(self):
        for item in self.data:
            yield item


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chembl_pipeline_e2e(minio_service, redis_client):
    """
    End-to-end test for the ChEMBL Activity pipeline.

    This test runs the pipeline with a mock data source and verifies
    that the data is written to the Bronze, Silver, and Gold layers.
    """
    # 1. Mock the data source
    mock_data_source = AsyncMock()
    mock_data_source.fetch.return_value = AsyncIterator(
        [
            {
                "activity_id": 1,
                "molecule_chembl_id": "CHEMBL1",
                "target_chembl_id": "CHEMBL2",
                "assay_chembl_id": "CHEMBL3",
                "standard_type": "IC50",
                "standard_value": "10.0",
                "standard_units": "nM",
            }
        ]
    )

    # 2. Initialize the pipeline
    storage = MemoryStorage()
    lock = RedisDistributedLock(redis_client)
    checkpoint = S3Checkpoint(
        bucket="checkpoints",
        endpoint_url=minio_service,
        access_key="minioadmin",
        secret_key="minioadmin",
    )

    pipeline = ChEMBLActivityPipeline(
        run_type=RunType.INCREMENTAL,
        data_source=mock_data_source,
        storage=storage,
        lock=lock,
        checkpoint=checkpoint,
        quarantine=AsyncMock(),
        resume=False,
    )

    # 3. Run the pipeline
    await pipeline.run()

    # 4. Verify the results
    assert len(storage.data) == 3
    assert "bronze/chembl/activity" in next(iter(storage.data.keys()))
    assert "chembl.activity" in storage.data
    assert "chembl.activity_gold" in storage.data
