"""Unit tests for ChEMBL DDD integration."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline
from bioetl.domain.config import PipelineConfig, RuntimeConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


@pytest.fixture
def chembl_pipeline() -> ChEMBLActivityPipeline:
    config = PipelineConfig(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type="activity",
        primary_keys=["activity_id"],
        silver_table="chembl_activity",
    )
    runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)
    logger = MagicMock()
    logger.bind.return_value = MagicMock()

    services = PipelineServices(
        data_source=AsyncMock(),
        storage=AsyncMock(),
        lock=AsyncMock(),
        checkpoint=AsyncMock(),
        quarantine=AsyncMock(),
        metrics=MagicMock(),
        tracing=MagicMock(),
        logger=logger,
    )
    run_id = uuid4()
    return ChEMBLActivityPipeline(
        config=config, runtime=runtime, services=services, run_id=run_id
    )


@pytest.fixture
def context(chembl_pipeline) -> PipelineContext:
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=chembl_pipeline.logger,
    )


@pytest.mark.asyncio
async def test_transform_valid_record(chembl_pipeline, context):
    """Verify that a valid record is correctly transformed."""
    record = {
        "activity_id": "100",
        "molecule_chembl_id": "M1",
        "pchembl_value": 5.5,
        "standard_value": 100,
    }
    result = await chembl_pipeline.transform_bronze_to_silver(context, record)
    assert result is not None
    assert result["activity_id"] == "100"
    assert result["pchembl_value"] == 5.5


@pytest.mark.asyncio
async def test_transform_invalid_pchembl(chembl_pipeline, context):
    """Verify that a negative pChemBL value causes the record to be skipped (Domain Invariant)."""
    record = {
        "activity_id": "101",
        "molecule_chembl_id": "M1",
        "pchembl_value": -1.0,  # INVALID
        "standard_value": 100,
    }
    result = await chembl_pipeline.transform_bronze_to_silver(context, record)

    # Should be None because validation failed and caught
    assert result is None

    # Verify warning was logged
    chembl_pipeline.logger.warning.assert_called()
    call_args = chembl_pipeline.logger.warning.call_args
    assert "entity_validation_failed" in call_args[0]


@pytest.mark.asyncio
async def test_transform_missing_id(chembl_pipeline, context):
    """Verify that missing activity_id returns None."""
    record = {"pchembl_value": 5.0}
    result = await chembl_pipeline.transform_bronze_to_silver(context, record)
    assert result is None
