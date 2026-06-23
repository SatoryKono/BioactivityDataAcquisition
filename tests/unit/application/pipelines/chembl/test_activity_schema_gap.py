"""Unit tests for ChEMBL Activity Entity schema gap fix."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

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
    run_id = deterministic_uuid_from_callsite("test_activity_schema_gap")
    transformer = ActivityTransformer(
        provider="chembl", dependencies=build_test_transformer_dependencies()
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
        run_id=deterministic_uuid_from_callsite("test_activity_schema_gap"),
        run_type=RunType.INCREMENTAL,
        logger=chembl_pipeline.logger,
    )


@pytest.mark.asyncio
async def test_transform_populates_extended_fields(chembl_pipeline, context):
    """Verify that new fields (assay_type, publication_year, etc.) are correctly propagated via Entity."""
    record = {
        "activity_id": "100",
        "molecule_chembl_id": "M1",
        "pchembl_value": 5.5,
        "standard_value": 100,
        # New fields
        "assay_type": "B",
        "assay_description": "Test Assay",
        "document_chembl_id": "CHEMBL123",
        "document_year": 2023,
    }

    result = await chembl_pipeline.transform_bronze_to_silver(context, record)

    assert result is not None
    assert result["activity_id"] == "100"
    # Verify extended fields are present in SilverRecord
    assert result["assay_type"] == "B"
    assert result["assay_description"] == "Test Assay"
    assert result["publication_id"] == "CHEMBL123"
    assert result["publication_year"] == 2023
    assert result["_run_id"] == str(context.run_id)
    assert result["_run_type"] == context.run_type.value
    assert "_ingestion_ts" in result


@pytest.mark.asyncio
async def test_transform_handles_missing_extended_fields(chembl_pipeline, context):
    """Verify that missing extended fields result in None/null in SilverRecord (backward compatibility)."""
    record = {
        "activity_id": "100",
        "molecule_chembl_id": "M1",
        "pchembl_value": 5.5,
        # Extended fields missing
    }

    result = await chembl_pipeline.transform_bronze_to_silver(context, record)

    assert result is not None
    assert result["assay_type"] is None
    assert result["publication_year"] is None
