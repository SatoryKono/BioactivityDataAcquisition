"""Unit tests for ChEMBL pipelines (Assay, Document, Molecule, Target)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.application.pipelines.chembl import (
    AssayTransformer,
    ChEMBLAssayPipeline,
    ChEMBLMoleculePipeline,
    ChEMBLPublicationPipeline,
    ChEMBLTargetPipeline,
    MoleculeTransformer,
    PublicationTransformer,
    TargetTransformer,
)
from bioetl.domain.config import PipelineConfig, RuntimeConfig, TableConfig
from bioetl.domain.types import RunID, RunType
from bioetl.domain.ports.noop import NoOpMetrics
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


@pytest.fixture
def mock_services():
    """Create mock pipeline services."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)

    return PipelineService(
        data_source=AsyncMock(),
        storage=MagicMock(),
        lock=AsyncMock(),
        checkpoint=MagicMock(),
        quarantine=MagicMock(),
        metrics=NoOpMetrics(warn_on_use=False),
        tracing=MagicMock(),
        logger=mock_logger,
    )


@pytest.fixture
def runtime_config():
    """Create runtime configuration."""
    return RuntimeConfig(
        run_type=RunType.INCREMENTAL,
        resume=False,
    )


@pytest.fixture
def run_id() -> RunID:
    """Create a test run ID."""
    return uuid4()


def create_pipeline_config(
    pipeline_name: str,
    entity_type: str,
    silver_table: str,
    primary_keys: list[str],
) -> PipelineConfig:
    """Helper to create pipeline config."""
    return PipelineConfig(
        pipeline_name=pipeline_name,
        provider="chembl",
        entity_type=entity_type,
        table=TableConfig(
            primary_keys=primary_keys,
            silver_table=silver_table,
        ),
    )


@pytest.mark.unit
class TestChEMBLAssayPipeline:
    """Tests for ChEMBLAssayPipeline."""

    @pytest.fixture
    def pipeline(self, mock_services, runtime_config, run_id):
        """Create assay pipeline instance."""
        config = create_pipeline_config(
            pipeline_name="chembl_assay",
            entity_type="assay",
            silver_table="chembl.assay",
            primary_keys=["assay_id"],
        )
        return ChEMBLAssayPipeline(
            config=config,
            runtime=runtime_config,
            services=mock_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=AssayTransformer(
                provider="chembl", dependencies=build_test_transformer_dependencies()
            ),
        )

    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initializes correctly."""
        assert pipeline.provider == "chembl"
        assert pipeline._transformer is not None

    @pytest.mark.asyncio
    async def test_transform_bronze_to_silver(self, pipeline):
        """Test transformation of assay record."""
        record = {
            "assay_chembl_id": "CHEMBL123456",
            "target_chembl_id": "CHEMBL123",
            "assay_type": "B",
        }

        result = await pipeline.transform_bronze_to_silver(pipeline.context, record)

        assert result is not None
        assert result["assay_id"] == "CHEMBL123456"
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_bronze_to_silver_missing_id(self, pipeline):
        """Test transformation returns None for missing ID."""
        record = {"target_id": "CHEMBL123"}

        result = await pipeline.transform_bronze_to_silver(pipeline.context, record)

        assert result is None


@pytest.mark.unit
class TestChEMBLPublicationPipeline:
    """Tests for ChEMBLPublicationPipeline."""

    @pytest.fixture
    def pipeline(self, mock_services, runtime_config, run_id):
        """Create publication pipeline instance."""
        config = create_pipeline_config(
            pipeline_name="chembl_publication",
            entity_type="publication",
            silver_table="chembl.publication",
            primary_keys=["publication_id"],
        )
        return ChEMBLPublicationPipeline(
            config=config,
            runtime=runtime_config,
            services=mock_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=PublicationTransformer(
                provider="chembl", dependencies=build_test_transformer_dependencies()
            ),
        )

    def test_l_publication_pipeline__initialization__447070d2(self, pipeline):
        """Test pipeline initializes correctly."""
        assert pipeline.provider == "chembl"
        assert pipeline._transformer is not None

    @pytest.mark.asyncio
    async def test_l_publication_pipeline__bronze_to_silver__9ba864bb(self, pipeline):
        """Test transformation of document record."""
        record = {
            "publication_id": "CHEMBL789012",
            "document_chembl_id": "CHEMBL789012",
            "title": "Test Document",
            "pmid": "12345678",
        }

        result = await pipeline.transform_bronze_to_silver(pipeline.context, record)

        assert result is not None
        assert result["publication_id"] == "CHEMBL789012"
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_l_publication_pipeline__to_silver_missing_id__f172be02(
        self, pipeline
    ):
        """Test transformation returns None for missing ID."""
        record = {"title": "Test Document"}

        result = await pipeline.transform_bronze_to_silver(pipeline.context, record)

        assert result is None


@pytest.mark.unit
class TestChEMBLMoleculePipeline:
    """Tests for ChEMBLMoleculePipeline."""

    @pytest.fixture
    def pipeline(self, mock_services, runtime_config, run_id):
        """Create molecule pipeline instance."""
        config = create_pipeline_config(
            pipeline_name="chembl_molecule",
            entity_type="molecule",
            silver_table="chembl.molecule",
            primary_keys=["molecule_id"],
        )
        return ChEMBLMoleculePipeline(
            config=config,
            runtime=runtime_config,
            services=mock_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=MoleculeTransformer(
                provider="chembl", dependencies=build_test_transformer_dependencies()
            ),
        )

    def test_b_l_molecule_pipeline__initialization__04e9e507(self, pipeline):
        """Test pipeline initializes correctly."""
        assert pipeline.provider == "chembl"
        assert pipeline._transformer is not None

    @pytest.mark.asyncio
    async def test_b_l_molecule_pipeline__bronze_to_silver__80683c68(self, pipeline):
        """Test transformation of molecule record."""
        record = {
            "molecule_chembl_id": "CHEMBL25",
            "pref_name": "ASPIRIN",
            "molecule_type": "Small molecule",
        }

        result = await pipeline.transform_bronze_to_silver(pipeline.context, record)

        assert result is not None
        assert result["molecule_id"] == "CHEMBL25"
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_b_l_molecule_pipeline__to_silver_missing_id__1f76351e(
        self, pipeline
    ):
        """Test transformation returns None for missing ID."""
        record = {"pref_name": "ASPIRIN"}

        result = await pipeline.transform_bronze_to_silver(pipeline.context, record)

        assert result is None


@pytest.mark.unit
class TestChEMBLTargetPipeline:
    """Tests for ChEMBLTargetPipeline."""

    @pytest.fixture
    def pipeline(self, mock_services, runtime_config, run_id):
        """Create target pipeline instance."""
        config = create_pipeline_config(
            pipeline_name="chembl_target",
            entity_type="target",
            silver_table="chembl.target",
            primary_keys=["target_id"],
        )
        return ChEMBLTargetPipeline(
            config=config,
            runtime=runtime_config,
            services=mock_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=TargetTransformer(
                provider="chembl", dependencies=build_test_transformer_dependencies()
            ),
        )

    def test_m_b_l_target_pipeline__initialization__a251c649(self, pipeline):
        """Test pipeline initializes correctly."""
        assert pipeline.provider == "chembl"
        assert pipeline._transformer is not None

    @pytest.mark.asyncio
    async def test_m_b_l_target_pipeline__bronze_to_silver__b4e98d52(self, pipeline):
        """Test transformation of target record."""
        record = {
            "target_chembl_id": "CHEMBL1862",
            "pref_name": "Cyclooxygenase-2",
            "target_type": "SINGLE PROTEIN",
        }

        result = await pipeline.transform_bronze_to_silver(pipeline.context, record)

        assert result is not None
        assert result["target_id"] == "CHEMBL1862"
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_m_b_l_target_pipeline__to_silver_missing_id__c57d00f6(
        self, pipeline
    ):
        """Test transformation returns None for missing ID."""
        record = {"pref_name": "COX-2"}

        result = await pipeline.transform_bronze_to_silver(pipeline.context, record)

        assert result is None
