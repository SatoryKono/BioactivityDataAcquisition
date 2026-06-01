"""Unit tests for ChEMBL DDD integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.application.pipelines.chembl import ChEMBLActivityPipeline
from bioetl.application.pipelines.chembl.activity_transformer import ActivityTransformer
from bioetl.domain.config import PipelineConfig, RuntimeConfig, TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


@pytest.fixture
def chembl_pipeline() -> ChEMBLActivityPipeline:
    config = PipelineConfig(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type="activity",
        table=TableConfig(
            primary_keys=["activity_id"],
            silver_table="chembl_activity",
        ),
    )
    runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)
    logger = MagicMock()
    logger.bind.return_value = MagicMock()

    services = PipelineService(
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
    transformer = ActivityTransformer(
        dependencies=build_test_transformer_dependencies()
    )
    return ChEMBLActivityPipeline(
        config=config,
        runtime=runtime,
        services=services,
        run_id=run_id,
        shutdown_signal=ShutdownSignal(),
        transformer=transformer,
    )


@pytest.fixture
def context(chembl_pipeline) -> PipelineContext:
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=chembl_pipeline.logger,
    )


@pytest.mark.asyncio
async def test_chembl_chembl_ddd__valid_record__639aa6d2(chembl_pipeline, context):
    """Verify that a valid record is correctly transformed."""
    record = {
        "activity_id": "100",
        "molecule_id": "M1",
        "pchembl_value": 5.5,
        "standard_value": 100,
    }
    result = await chembl_pipeline.transform_bronze_to_silver(context, record)
    assert result is not None
    assert result["activity_id"] == "100"
    assert result["pchembl_value"] == pytest.approx(5.5)
    assert result["_run_id"] == str(context.run_id)
    assert result["_run_type"] == context.run_type.value
    assert "_ingestion_ts" in result


@pytest.mark.asyncio
async def test_transform_invalid_pchembl(chembl_pipeline, context):
    """Verify that a negative pChemBL value causes the record to be skipped (Domain Invariant)."""
    record = {
        "activity_id": "101",
        "molecule_id": "M1",
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
