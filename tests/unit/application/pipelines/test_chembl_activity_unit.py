"""Unit tests for the ChEMBLActivityPipeline."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline
from uuid import uuid4

from bioetl.domain.config import RuntimeConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from bioetl.infrastructure.config import get_pipeline_config
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics


@pytest.fixture
def chembl_pipeline():
    """Fixture for a ChEMBLActivityPipeline."""
    runtime = RuntimeConfig(
        run_type=RunType.INCREMENTAL,
        resume=False,
    )
    # Mock logger with bind method
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)

    services = PipelineServices(
        data_source=AsyncMock(),
        storage=MagicMock(),
        lock=AsyncMock(),
        checkpoint=MagicMock(),
        quarantine=MagicMock(),
        metrics=NoOpMetrics(warn_on_use=False),
        tracing=MagicMock(),
        logger=mock_logger,
    )
    config = get_pipeline_config("chembl_activity")
    run_id = uuid4()
    pipeline = ChEMBLActivityPipeline.create(
        run_id=run_id, runtime=runtime, services=services, config=config
    )
    return pipeline


async def test_chembl_transform_bronze_to_silver_happy_path(chembl_pipeline):
    """Test the transform_bronze_to_silver method with a valid record."""
    record = {
        "activity_id": 123,
        "molecule_chembl_id": "CHEMBL1",
        "target_chembl_id": "CHEMBL2",
        "assay_chembl_id": "CHEMBL3",
        "standard_type": "IC50",
        "standard_value": "10.5",
        "standard_units": "nM",
    }
    context = PipelineContext(
        run_id=chembl_pipeline.context.run_id,
        run_type=chembl_pipeline.context.run_type,
        logger=MagicMock(),
    )
    transformed = await chembl_pipeline.transform_bronze_to_silver(context, record)
    assert transformed is not None
    assert transformed["activity_id"] == "123"
    assert transformed["standard_value"] == 10.5


async def test_chembl_transform_bronze_to_silver_no_activity_id(chembl_pipeline):
    """Test that records with no activity_id are skipped."""
    record = {"molecule_chembl_id": "CHEMBL1"}
    context = PipelineContext(
        run_id=chembl_pipeline.context.run_id,
        run_type=chembl_pipeline.context.run_type,
        logger=MagicMock(),
    )
    transformed = await chembl_pipeline.transform_bronze_to_silver(context, record)
    assert transformed is None


def test_chembl_should_write_gold_true(chembl_pipeline):
    """Test the should_write_gold method with a valid record."""
    record = {
        "standard_value": 10.5,
        "standard_units": "nM",
        "target_chembl_id": "CHEMBL2",
        "standard_type": "IC50",
        "standard_relation": "=",
        "assay_type": "B",
        "potential_duplicate": "0",
    }
    context = PipelineContext(
        run_id=chembl_pipeline.context.run_id,
        run_type=chembl_pipeline.context.run_type,
        logger=MagicMock(),
    )
    assert chembl_pipeline.should_write_gold(context, record) is True


def test_chembl_should_write_gold_false(chembl_pipeline):
    """Test the should_write_gold method with invalid records."""
    context = PipelineContext(
        run_id=chembl_pipeline.context.run_id,
        run_type=chembl_pipeline.context.run_type,
        logger=MagicMock(),
    )
    # No standard value
    record1 = {
        "standard_units": "nM",
        "target_chembl_id": "CHEMBL2",
        "standard_type": "IC50",
    }
    assert chembl_pipeline.should_write_gold(context, record1) is False

    # No standard units
    record2 = {
        "standard_value": 10.5,
        "target_chembl_id": "CHEMBL2",
        "standard_type": "IC50",
    }
    assert chembl_pipeline.should_write_gold(context, record2) is False

    # No target
    record3 = {"standard_value": 10.5, "standard_units": "nM", "standard_type": "IC50"}
    assert chembl_pipeline.should_write_gold(context, record3) is False

    # Wrong type
    record4 = {
        "standard_value": 10.5,
        "standard_units": "nM",
        "target_chembl_id": "CHEMBL2",
        "standard_type": "Other",
    }
    assert chembl_pipeline.should_write_gold(context, record4) is False
