"""End-to-end tests for ChEMBL Activity Pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from bioetl.application.pipelines.chembl_activity import ChEMBLActivityPipeline
from bioetl.domain.types import RunType, HealthStatus, Watermark, BatchID
from bioetl.domain.ports import DataSourcePort, StoragePort, LockPort, CheckpointPort, QuarantinePort
from datetime import datetime, UTC
import structlog

class InMemoryStorage(StoragePort):
    """In-memory storage for e2e tests."""

    def __init__(self):
        self.bronze_records = []
        self.silver_records = []
        self.gold_records = []

    def write_bronze(self, records, **kwargs):
        # Flatten batches if necessary, but here we assume list of records
        self.bronze_records.extend(records)
        return BatchID(uuid4())

    def write_silver(self, table_name, records, **kwargs):
        self.silver_records.extend(records)

    def write_gold(self, table_name, records, **kwargs):
        self.gold_records.extend(records)

    def commit(self):
        pass

    def rollback(self):
        pass

class MockChemblAdapter(DataSourcePort):
    """Mock ChEMBL adapter for e2e tests."""

    provider_name = "chembl"

    def __init__(self, records: list):
        self._records = records

    async def fetch(self, entity_type, watermark=None, limit=None):
        for record in self._records:
            yield record

    async def health_check(self):
        return HealthStatus.HEALTHY

    async def get_latest_watermark(self):
        return None

@pytest.fixture
def sample_chembl_records():
    """Sample ChEMBL activity records."""
    return [
        {
            "activity_id": 12345,
            "molecule_chembl_id": "CHEMBL25",
            "target_chembl_id": "CHEMBL1824",
            "assay_chembl_id": "CHEMBL123456",
            "standard_type": "IC50",
            "standard_value": "50.0",
            "standard_units": "nM",
            "standard_relation": "=",
            "assay_type": "B",
            "pchembl_value": "7.3",
            "document_chembl_id": "CHEMBL1122",
            "document_year": 2020
        },
        {
            "activity_id": 12346,
            "molecule_chembl_id": "CHEMBL26",
            "target_chembl_id": "CHEMBL1825",
            "assay_chembl_id": "CHEMBL123457",
            "standard_type": "Ki",
            "standard_value": "100.0",
            "standard_units": "nM",
            "standard_relation": "=",
            "assay_type": "B",
            "pchembl_value": "7.0",
            "document_chembl_id": "CHEMBL1123",
            "document_year": 2021
        },
        # Record without standard_value - should not go to Gold
        {
            "activity_id": 12347,
            "molecule_chembl_id": "CHEMBL27",
            "target_chembl_id": "CHEMBL1826",
            "assay_chembl_id": "CHEMBL123458",
            "standard_type": "IC50",
            "standard_value": None,
            "standard_units": "nM",
            "document_chembl_id": "CHEMBL1124",
            "document_year": 2022
        },
    ]

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_chembl_pipeline_full_flow(sample_chembl_records):
    """E2E: Extract -> Bronze -> Silver -> Gold."""
    # Setup
    mock_adapter = MockChemblAdapter(sample_chembl_records)
    storage = InMemoryStorage()

    # Mock lock, checkpoint, quarantine
    mock_lock = AsyncMock(spec=LockPort)
    mock_lock.acquire.return_value = True
    mock_lock.release.return_value = True
    mock_lock.heartbeat.return_value = True

    mock_checkpoint = AsyncMock(spec=CheckpointPort)
    mock_checkpoint.load.return_value = None

    mock_quarantine = AsyncMock(spec=QuarantinePort)

    logger = structlog.get_logger()

    # Create pipeline
    pipeline = ChEMBLActivityPipeline(
        run_type=RunType.INCREMENTAL,
        data_source=mock_adapter,
        storage=storage,
        lock=mock_lock,
        checkpoint=mock_checkpoint,
        quarantine=mock_quarantine,
        resume=False,
        logger=logger
    )

    # Execute
    await pipeline.run()

    # Assert Bronze (all records)
    assert len(storage.bronze_records) == 3

    # Assert Silver (all records transformed)
    assert len(storage.silver_records) == 3
    # Check normalization
    assert storage.silver_records[0]["entity_id"].startswith("chembl:")
    assert isinstance(storage.silver_records[0]["standard_value"], float)
    assert storage.silver_records[0]["standard_value"] == 50.0

    # Assert Gold (only records passing quality filter)
    # Records with standard_value and preferred types go to Gold
    assert len(storage.gold_records) == 2

    gold_ids = [r["activity_id"] for r in storage.gold_records]
    assert "12345" in gold_ids
    assert "12346" in gold_ids
    assert "12347" not in gold_ids  # Missing standard_value


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_chembl_pipeline_empty_source():
    """E2E: Pipeline with no records."""
    mock_adapter = MockChemblAdapter([])
    storage = InMemoryStorage()

    mock_lock = AsyncMock(spec=LockPort)
    mock_lock.acquire.return_value = True
    mock_lock.release.return_value = True
    mock_lock.heartbeat.return_value = True

    mock_checkpoint = AsyncMock(spec=CheckpointPort)
    mock_checkpoint.load.return_value = None

    mock_quarantine = AsyncMock(spec=QuarantinePort)

    logger = structlog.get_logger()

    pipeline = ChEMBLActivityPipeline(
        run_type=RunType.INCREMENTAL,
        data_source=mock_adapter,
        storage=storage,
        lock=mock_lock,
        checkpoint=mock_checkpoint,
        quarantine=mock_quarantine,
        logger=logger
    )

    await pipeline.run()

    assert len(storage.bronze_records) == 0
    assert len(storage.silver_records) == 0
    assert len(storage.gold_records) == 0
