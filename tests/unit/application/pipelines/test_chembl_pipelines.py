"""Unit tests for ChEMBL pipelines (Assay, Document, Molecule, Target)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.pipelines.chembl.assay import ChEMBLAssayPipeline
from bioetl.application.pipelines.chembl.document import ChEMBLDocumentPipeline
from bioetl.application.pipelines.chembl.molecule import ChEMBLMoleculePipeline
from bioetl.application.pipelines.chembl.target import ChEMBLTargetPipeline
from bioetl.domain.config import PipelineConfig, RuntimeConfig
from bioetl.domain.types import RunType
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics


@pytest.fixture
def mock_services():
    """Create mock pipeline services."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)

    return PipelineServices(
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
        primary_keys=primary_keys,
        silver_table=silver_table,
        watermark_field=f"{entity_type}_chembl_id",
    )


@pytest.mark.unit
class TestChEMBLAssayPipeline:
    """Tests for ChEMBLAssayPipeline."""

    @pytest.fixture
    def pipeline(self, mock_services, runtime_config):
        """Create assay pipeline instance."""
        config = create_pipeline_config(
            pipeline_name="chembl_assay",
            entity_type="assay",
            silver_table="chembl.assay",
            primary_keys=["assay_chembl_id"],
        )
        return ChEMBLAssayPipeline(
            config=config,
            runtime=runtime_config,
            services=mock_services,
        )

    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initializes correctly."""
        assert pipeline.provider == "chembl"
        assert pipeline._transformer is not None
        assert pipeline._watermark_extractor is not None

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
        assert result["assay_chembl_id"] == "CHEMBL123456"

    @pytest.mark.asyncio
    async def test_transform_bronze_to_silver_missing_id(self, pipeline):
        """Test transformation returns None for missing ID."""
        record = {"target_chembl_id": "CHEMBL123"}

        result = await pipeline.transform_bronze_to_silver(pipeline.context, record)

        assert result is None

    def test_extract_watermark(self, pipeline):
        """Test watermark extraction."""
        record = {"assay_chembl_id": "CHEMBL123456"}

        watermark = pipeline.extract_watermark(pipeline.context, record)

        assert watermark.value == "CHEMBL123456"


@pytest.mark.unit
class TestChEMBLDocumentPipeline:
    """Tests for ChEMBLDocumentPipeline."""

    @pytest.fixture
    def pipeline(self, mock_services, runtime_config):
        """Create document pipeline instance."""
        config = create_pipeline_config(
            pipeline_name="chembl_document",
            entity_type="document",
            silver_table="chembl.document",
            primary_keys=["document_chembl_id"],
        )
        return ChEMBLDocumentPipeline(
            config=config,
            runtime=runtime_config,
            services=mock_services,
        )

    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initializes correctly."""
        assert pipeline.provider == "chembl"
        assert pipeline._transformer is not None
        assert pipeline._watermark_extractor is not None

    @pytest.mark.asyncio
    async def test_transform_bronze_to_silver(self, pipeline):
        """Test transformation of document record."""
        record = {
            "document_chembl_id": "CHEMBL789012",
            "title": "Test Document",
            "pubmed_id": 12345678,
        }

        result = await pipeline.transform_bronze_to_silver(pipeline.context, record)

        assert result is not None
        assert result["document_chembl_id"] == "CHEMBL789012"

    @pytest.mark.asyncio
    async def test_transform_bronze_to_silver_missing_id(self, pipeline):
        """Test transformation returns None for missing ID."""
        record = {"title": "Test Document"}

        result = await pipeline.transform_bronze_to_silver(pipeline.context, record)

        assert result is None

    def test_extract_watermark(self, pipeline):
        """Test watermark extraction."""
        record = {"document_chembl_id": "CHEMBL789012"}

        watermark = pipeline.extract_watermark(pipeline.context, record)

        assert watermark.value == "CHEMBL789012"


@pytest.mark.unit
class TestChEMBLMoleculePipeline:
    """Tests for ChEMBLMoleculePipeline."""

    @pytest.fixture
    def pipeline(self, mock_services, runtime_config):
        """Create molecule pipeline instance."""
        config = create_pipeline_config(
            pipeline_name="chembl_molecule",
            entity_type="molecule",
            silver_table="chembl.molecule",
            primary_keys=["molecule_chembl_id"],
        )
        return ChEMBLMoleculePipeline(
            config=config,
            runtime=runtime_config,
            services=mock_services,
        )

    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initializes correctly."""
        assert pipeline.provider == "chembl"
        assert pipeline._transformer is not None
        assert pipeline._watermark_extractor is not None

    @pytest.mark.asyncio
    async def test_transform_bronze_to_silver(self, pipeline):
        """Test transformation of molecule record."""
        record = {
            "molecule_chembl_id": "CHEMBL25",
            "pref_name": "ASPIRIN",
            "molecule_type": "Small molecule",
        }

        result = await pipeline.transform_bronze_to_silver(pipeline.context, record)

        assert result is not None
        assert result["molecule_chembl_id"] == "CHEMBL25"

    @pytest.mark.asyncio
    async def test_transform_bronze_to_silver_missing_id(self, pipeline):
        """Test transformation returns None for missing ID."""
        record = {"pref_name": "ASPIRIN"}

        result = await pipeline.transform_bronze_to_silver(pipeline.context, record)

        assert result is None

    def test_extract_watermark(self, pipeline):
        """Test watermark extraction."""
        record = {"molecule_chembl_id": "CHEMBL25"}

        watermark = pipeline.extract_watermark(pipeline.context, record)

        assert watermark.value == "CHEMBL25"


@pytest.mark.unit
class TestChEMBLTargetPipeline:
    """Tests for ChEMBLTargetPipeline."""

    @pytest.fixture
    def pipeline(self, mock_services, runtime_config):
        """Create target pipeline instance."""
        config = create_pipeline_config(
            pipeline_name="chembl_target",
            entity_type="target",
            silver_table="chembl.target",
            primary_keys=["target_chembl_id"],
        )
        return ChEMBLTargetPipeline(
            config=config,
            runtime=runtime_config,
            services=mock_services,
        )

    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initializes correctly."""
        assert pipeline.provider == "chembl"
        assert pipeline._transformer is not None
        assert pipeline._watermark_extractor is not None

    @pytest.mark.asyncio
    async def test_transform_bronze_to_silver(self, pipeline):
        """Test transformation of target record."""
        record = {
            "target_chembl_id": "CHEMBL1862",
            "pref_name": "Cyclooxygenase-2",
            "target_type": "SINGLE PROTEIN",
        }

        result = await pipeline.transform_bronze_to_silver(pipeline.context, record)

        assert result is not None
        assert result["target_chembl_id"] == "CHEMBL1862"

    @pytest.mark.asyncio
    async def test_transform_bronze_to_silver_missing_id(self, pipeline):
        """Test transformation returns None for missing ID."""
        record = {"pref_name": "COX-2"}

        result = await pipeline.transform_bronze_to_silver(pipeline.context, record)

        assert result is None

    def test_extract_watermark(self, pipeline):
        """Test watermark extraction."""
        record = {"target_chembl_id": "CHEMBL1862"}

        watermark = pipeline.extract_watermark(pipeline.context, record)

        assert watermark.value == "CHEMBL1862"
