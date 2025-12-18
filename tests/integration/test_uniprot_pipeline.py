"""Integration tests for the UniProt Protein pipeline.

Тестирует E2E трансформации и интеграцию с инфраструктурой.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.uniprot_protein import UniProtProteinPipeline
from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.domain.pipeline_config import PipelineConfig
from bioetl.domain.types import RunType
from bioetl.domain.context import PipelineContext


@pytest.fixture
def uniprot_config() -> PipelineConfig:
    """Создаёт конфигурацию UniProt пайплайна."""
    return PipelineConfig(
        pipeline_name="uniprot_protein",
        provider="uniprot",
        entity_type="protein",
        primary_keys=["accession"],
        silver_table="uniprot.protein",
        gold_table="uniprot.protein_gold",
        batch_size=100,
        checkpoint_interval=1000,
        fields=[
            "accession",
            "entry_name",
            "protein_name",
            "gene_names",
            "organism_id",
            "sequence_length",
        ],
    )


@pytest.fixture
def uniprot_runtime() -> PipelineRuntimeConfig:
    """Создаёт runtime конфигурацию."""
    return PipelineRuntimeConfig(
        run_type=RunType.INCREMENTAL,
        resume=False,
        limit=None,
    )


@pytest.fixture
def mock_uniprot_services(mock_logger) -> PipelineServices:
    """Создаёт mock сервисы для тестирования."""
    mock_data_source = AsyncMock()
    mock_data_source.provider_name = "uniprot"
    mock_data_source.aclose = AsyncMock()

    mock_storage = AsyncMock()
    mock_storage.write_bronze = AsyncMock()
    mock_storage.write_silver = AsyncMock()
    mock_storage.write_gold = AsyncMock()
    mock_storage.aclose = AsyncMock()

    mock_lock = AsyncMock()
    mock_lock.acquire = AsyncMock(return_value=True)
    mock_lock.release = AsyncMock()

    mock_checkpoint = AsyncMock()
    mock_checkpoint.get_latest = AsyncMock(return_value=None)
    mock_checkpoint.save = AsyncMock()

    mock_quarantine = AsyncMock()
    mock_metrics = MagicMock()

    import structlog
    logger = structlog.get_logger()

    return PipelineServices(
        data_source=mock_data_source,
        storage=mock_storage,
        lock=mock_lock,
        checkpoint=mock_checkpoint,
        quarantine=mock_quarantine,
        metrics=mock_metrics,
        logger=logger,
    )


@pytest.fixture
def mock_logger():
    """Создаёт mock логгер."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


@pytest.mark.integration
class TestUniProtProteinPipelineTransform:
    """Тесты трансформации UniProt пайплайна."""

    async def test_transform_bronze_to_silver_complete_record(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест трансформации полной записи Bronze → Silver."""
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
        )

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        # Full UniProt record structure
        bronze_record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "MYC_HUMAN",
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {
                        "value": "Myc proto-oncogene protein"
                    }
                }
            },
            "genes": [
                {"geneName": {"value": "MYC"}},
                {"geneName": {"value": "BHLHE39"}},
            ],
            "organism": {
                "taxonId": 9606
            },
            "sequence": {
                "length": 439,
                "value": "MDFFRVVENQQPPATMPLNVSFTNRNYDLDYD..."
            },
        }

        silver_record = await pipeline.transform_bronze_to_silver(context, bronze_record)

        assert silver_record is not None
        assert silver_record["accession"] == "P12345"
        assert silver_record["entry_name"] == "MYC_HUMAN"
        assert silver_record["protein_name"] == "Myc proto-oncogene protein"
        assert silver_record["gene_names"] == ["MYC", "BHLHE39"]
        assert silver_record["organism_id"] == 9606
        assert silver_record["sequence_length"] == 439
        assert "entity_id" in silver_record
        assert "content_hash" in silver_record

    async def test_transform_bronze_to_silver_minimal_record(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест трансформации минимальной записи."""
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
        )

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        # Minimal record
        bronze_record = {
            "primaryAccession": "Q99999",
            "uniProtkbId": "TEST_HUMAN",
        }

        silver_record = await pipeline.transform_bronze_to_silver(context, bronze_record)

        assert silver_record is not None
        assert silver_record["accession"] == "Q99999"
        assert silver_record["entry_name"] == "TEST_HUMAN"
        assert silver_record["protein_name"] is None
        assert silver_record["gene_names"] == []
        assert silver_record["organism_id"] is None
        assert silver_record["sequence_length"] is None
        assert "entity_id" in silver_record
        assert "content_hash" in silver_record

    async def test_transform_bronze_to_silver_missing_accession_returns_none(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест: запись без primaryAccession возвращает None."""
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
        )

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        bronze_record = {"uniProtkbId": "NO_ACCESSION"}  # No primaryAccession

        silver_record = await pipeline.transform_bronze_to_silver(context, bronze_record)

        assert silver_record is None

    async def test_transform_bronze_to_silver_missing_protein_description(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест трансформации записи без proteinDescription."""
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
        )

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        bronze_record = {
            "primaryAccession": "A0A000",
            "uniProtkbId": "UNKNOWN_HUMAN",
            "genes": [{"geneName": {"value": "GENE1"}}],
            "organism": {"taxonId": 9606},
            "sequence": {"length": 100},
        }

        silver_record = await pipeline.transform_bronze_to_silver(context, bronze_record)

        assert silver_record is not None
        assert silver_record["accession"] == "A0A000"
        assert silver_record["protein_name"] is None
        assert silver_record["gene_names"] == ["GENE1"]
        assert "entity_id" in silver_record

    async def test_transform_bronze_to_silver_empty_genes(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест трансформации записи с пустым списком генов."""
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
        )

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        bronze_record = {
            "primaryAccession": "B0B000",
            "uniProtkbId": "NOGENE_HUMAN",
            "genes": [],
        }

        silver_record = await pipeline.transform_bronze_to_silver(context, bronze_record)

        assert silver_record is not None
        assert silver_record["gene_names"] == []

    async def test_extract_watermark(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест извлечения watermark из записи."""
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
        )

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        record = {"primaryAccession": "P12345"}
        watermark = pipeline.extract_watermark(context, record)

        assert watermark == "P12345"

    async def test_extract_watermark_missing_accession(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест извлечения watermark при отсутствии accession."""
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
        )

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        record = {}  # No primaryAccession
        watermark = pipeline.extract_watermark(context, record)

        assert watermark == ""


@pytest.mark.integration
class TestUniProtProteinPipelineCreate:
    """Тесты создания UniProt пайплайна."""

    def test_create_pipeline(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест создания пайплайна через factory method."""
        pipeline = UniProtProteinPipeline.create(
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
            config=uniprot_config,
        )

        assert pipeline is not None
        assert isinstance(pipeline, UniProtProteinPipeline)
        assert pipeline.config == uniprot_config


@pytest.mark.integration
class TestUniProtProteinPipelineEdgeCases:
    """Тесты граничных случаев UniProt пайплайна."""

    async def test_transform_with_malformed_genes(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест трансформации с некорректной структурой genes."""
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
        )

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        # Malformed genes - missing geneName
        bronze_record = {
            "primaryAccession": "X00001",
            "genes": [
                {"geneName": {"value": "VALID"}},
                {"otherField": "no geneName"},
                {"geneName": {}},  # Empty geneName
            ],
        }

        silver_record = await pipeline.transform_bronze_to_silver(context, bronze_record)

        assert silver_record is not None
        # Should only include valid gene names
        assert "VALID" in silver_record["gene_names"]

    async def test_transform_with_none_organism(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест трансформации с None organism."""
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
        )

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        bronze_record = {
            "primaryAccession": "Y00001",
            "organism": None,
        }

        silver_record = await pipeline.transform_bronze_to_silver(context, bronze_record)

        assert silver_record is not None
        assert silver_record["organism_id"] is None
