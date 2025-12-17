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
    assert any("bronze/chembl/activity" in key for key in storage.data)
    assert any("silver/chembl.activity" in key for key in storage.data)
    assert any("gold/chembl.activity_gold" in key for key in storage.data)

    # Verify the content of the data
    bronze_data = next(
        value for key, value in storage.data.items() if "bronze/chembl/activity" in key
    )
    assert len(bronze_data) == 1
    assert bronze_data[0]["activity_id"] == 1

    silver_data = next(
        value for key, value in storage.data.items() if "silver/chembl.activity" in key
    )
    assert len(silver_data) == 1
    assert silver_data[0]["activity_id"] == 1

    gold_data = next(
        value
        for key, value in storage.data.items()
        if "gold/chembl.activity_gold" in key
    )
    assert len(gold_data) == 1
    assert gold_data[0]["activity_id"] == 1
    assert gold_data[0]["pchembl_value"] == 8.0
