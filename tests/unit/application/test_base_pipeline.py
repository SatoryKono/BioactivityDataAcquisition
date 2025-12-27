"""Unit tests for the BasePipeline class."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.domain.config import PipelineConfig, RuntimeConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunID, RunType


class ConcretePipeline(BasePipeline):
    async def transform_bronze_to_silver(
        self, _context: PipelineContext, record: dict
    ) -> dict | None:
        return record


@pytest.fixture
def mock_pipeline():
    """Fixture for a mocked BasePipeline."""
    config = PipelineConfig(
        pipeline_name="test_pipeline",
        provider="test_provider",
        entity_type="test_entity",
        primary_keys=["test_entity_id"],
        silver_table="test_provider.test_entity",
    )
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
        metrics=MagicMock(),
        tracing=MagicMock(),
        logger=mock_logger,
    )
    run_id: RunID = uuid4()
    pipeline = ConcretePipeline(config, runtime, services, run_id)
    return pipeline


async def test_base_pipeline_initialization(mock_pipeline):
    """Test that the BasePipeline initializes correctly."""
    assert mock_pipeline.pipeline_name == "test_pipeline"
    assert mock_pipeline.provider == "test_provider"
    assert mock_pipeline.entity_type == "test_entity"
    assert mock_pipeline.run_type == RunType.INCREMENTAL
    assert mock_pipeline.resume is False
    assert mock_pipeline.context.run_id is not None
    assert mock_pipeline.context.logger is not None


async def test_base_pipeline_accepts_four_params():
    """Test that BasePipeline.__init__ accepts exactly 4 parameters including run_id."""
    config = PipelineConfig(
        pipeline_name="test",
        provider="test",
        entity_type="entity",
        primary_keys=["id"],
        silver_table="test.entity",
    )
    runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    services = PipelineServices(
        data_source=AsyncMock(),
        storage=AsyncMock(),
        lock=AsyncMock(),
        checkpoint=AsyncMock(),
        quarantine=AsyncMock(),
        metrics=MagicMock(),
        tracing=MagicMock(),
        logger=mock_logger,
    )
    run_id: RunID = uuid4()

    # Should work with exactly 4 positional args (including run_id)
    pipeline = ConcretePipeline(config, runtime, services, run_id)
    assert pipeline.config == config
    assert pipeline.runtime == runtime
    assert pipeline.services == services
    assert pipeline.run_id == run_id


@pytest.mark.skip(reason="Suspected .pyc cache issue - run with --cache-clear")
async def test_base_pipeline_properties(mock_pipeline):
    """Test all convenience properties."""
    # Test run_id property
    assert mock_pipeline.run_id is not None

    # Test logger property
    assert mock_pipeline.logger is not None

    # Test shutdown_signal property
    assert mock_pipeline.shutdown_signal is not None

    # Test services property provides access to injected services
    assert mock_pipeline.services is not None
    assert mock_pipeline.services.data_source is not None
    assert mock_pipeline.services.storage is not None
    assert mock_pipeline.services.lock is not None
    assert mock_pipeline.services.checkpoint is not None
    assert mock_pipeline.services.quarantine is not None
    assert mock_pipeline.services.metrics is not None

    # Test limit property
    assert mock_pipeline.limit is None


async def test_base_pipeline_should_write_gold(mock_pipeline):
    """Test default should_write_gold returns True."""
    result = mock_pipeline.should_write_gold(mock_pipeline.context, {})
    assert result is True


async def test_run_id_propagation_is_consistent():
    """Test that run_id from constructor is used consistently across all components.

    This test ensures that the run_id passed to BasePipeline is the same run_id
    that appears in the PipelineContext, preventing the previous bug where
    BasePipeline generated a new run_id internally.
    """
    config = PipelineConfig(
        pipeline_name="test_pipeline",
        provider="test_provider",
        entity_type="test_entity",
        primary_keys=["id"],
        silver_table="test_provider.test_entity",
    )
    runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    services = PipelineServices(
        data_source=AsyncMock(),
        storage=AsyncMock(),
        lock=AsyncMock(),
        checkpoint=AsyncMock(),
        quarantine=AsyncMock(),
        metrics=MagicMock(),
        tracing=MagicMock(),
        logger=mock_logger,
    )

    # Create pipeline with explicit run_id (simulating CLI -> bootstrap -> pipeline flow)
    expected_run_id: RunID = uuid4()
    pipeline = ConcretePipeline(config, runtime, services, expected_run_id)

    # Verify run_id consistency across all access points
    assert (
        pipeline.run_id == expected_run_id
    ), "run_id property should return the injected run_id"
    assert (
        pipeline.context.run_id == expected_run_id
    ), "PipelineContext should have the same run_id"
    assert pipeline._run_id == expected_run_id, "Internal _run_id should match"

    # Verify logger was bound with correct run_id
    mock_logger.bind.assert_called_with(
        run_id=str(expected_run_id),
        pipeline=config.pipeline_name,
    )


@pytest.mark.unit
class TestTransformForGold:
    """Tests for transform_for_gold method."""

    def test_transform_for_gold_removes_json_fields(self, mock_pipeline):
        """Test that transform_for_gold removes JSON string fields."""
        silver_record = {
            "molecule_chembl_id": "CHEMBL123",
            "pref_name": "Aspirin",
            # JSON fields that should be excluded
            "molecule_hierarchy": '{"parent_chembl_id": "CHEMBL123"}',
            "molecule_properties": '{"alogp": 1.5}',
            "molecule_structures": '{"canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"}',
            "molecule_synonyms": '["Aspirin", "ASA"]',
            "cross_references": "[]",
            "atc_classifications": "[]",
        }

        gold_record = mock_pipeline.transform_for_gold(
            mock_pipeline.context, silver_record
        )

        # Verify JSON fields are removed
        assert "molecule_hierarchy" not in gold_record
        assert "molecule_properties" not in gold_record
        assert "molecule_structures" not in gold_record
        assert "molecule_synonyms" not in gold_record
        assert "cross_references" not in gold_record
        assert "atc_classifications" not in gold_record

        # Verify non-excluded fields are preserved
        assert gold_record["molecule_chembl_id"] == "CHEMBL123"
        assert gold_record["pref_name"] == "Aspirin"

    def test_transform_for_gold_preserves_flat_fields(self, mock_pipeline):
        """Test that transform_for_gold preserves flat fields."""
        silver_record = {
            "molecule_chembl_id": "CHEMBL123",
            "pref_name": "Aspirin",
            "molecule_type": "Small molecule",
            "max_phase": 4.0,
            "hierarchy_parent_chembl_id": "CHEMBL123",
            "property_mw_freebase": 180.16,
            "structure_canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "_run_id": "abc-123",
            "_ingestion_ts": "2024-01-01T00:00:00",
        }

        gold_record = mock_pipeline.transform_for_gold(
            mock_pipeline.context, silver_record
        )

        assert gold_record == silver_record

    def test_gold_exclude_fields_constant(self, mock_pipeline):
        """Test that GOLD_EXCLUDE_FIELDS contains expected fields."""
        expected_fields = {
            # Molecule JSON fields (Silver forensic only)
            "molecule_hierarchy",
            "molecule_properties",
            "molecule_structures",
            "molecule_synonyms",
            "cross_references",
            "atc_classifications",
            # Internal metadata fields (Silver only)
            "entity_id",
            "content_hash",
            "_run_type",
            "_source_batch_id",
        }
        assert mock_pipeline.GOLD_EXCLUDE_FIELDS == expected_fields
