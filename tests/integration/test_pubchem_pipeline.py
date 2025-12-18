"""Integration tests for the PubChem Compound pipeline.

Тестирует E2E трансформации и интеграцию с инфраструктурой.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.pubchem.compound import PubChemCompoundPipeline
from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.domain.pipeline_config import PipelineConfig
from bioetl.domain.types import RunType
from bioetl.domain.context import PipelineContext


@pytest.fixture
def pubchem_config() -> PipelineConfig:
    """Создаёт конфигурацию PubChem пайплайна."""
    return PipelineConfig(
        pipeline_name="pubchem_compound",
        provider="pubchem",
        entity_type="compound",
        primary_keys=["cid"],
        silver_table="pubchem.compound",
        gold_table="pubchem.compound_gold",
        batch_size=100,
        checkpoint_interval=1000,
        fields=[
            "cid",
            "molecular_formula",
            "molecular_weight",
            "canonical_smiles",
            "isomeric_smiles",
            "inchi",
            "inchikey",
            "iupac_name",
        ],
    )


@pytest.fixture
def pubchem_runtime() -> PipelineRuntimeConfig:
    """Создаёт runtime конфигурацию."""
    return PipelineRuntimeConfig(
        run_type=RunType.INCREMENTAL,
        resume=False,
        limit=None,
    )


@pytest.fixture
def mock_pubchem_services(mock_logger) -> PipelineServices:
    """Создаёт mock сервисы для тестирования."""
    mock_data_source = AsyncMock()
    mock_data_source.provider_name = "pubchem"
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
class TestPubChemCompoundPipelineTransform:
    """Тесты трансформации PubChem пайплайна."""

    async def test_transform_bronze_to_silver_complete_record(
        self,
        pubchem_config,
        pubchem_runtime,
        mock_pubchem_services,
    ):
        """Тест трансформации полной записи Bronze → Silver."""
        pipeline = PubChemCompoundPipeline(
            config=pubchem_config,
            runtime=pubchem_runtime,
            services=mock_pubchem_services,
        )

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_pubchem_services.logger,
        )

        bronze_record = {
            "cid": 2244,
            "molecular_formula": "C9H8O4",
            "molecular_weight": 180.16,
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "isomeric_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
            "inchikey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            "iupac_name": "2-acetyloxybenzoic acid",
        }

        silver_record = await pipeline.transform_bronze_to_silver(context, bronze_record)

        assert silver_record is not None
        assert silver_record["cid"] == "2244"  # Now string
        assert silver_record["molecular_formula"] == "C9H8O4"
        assert silver_record["molecular_weight"] == 180.16
        assert silver_record["canonical_smiles"] == "CC(=O)OC1=CC=CC=C1C(=O)O"
        assert silver_record["inchikey"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
        assert silver_record["iupac_name"] == "2-acetyloxybenzoic acid"
        assert "entity_id" in silver_record
        assert "content_hash" in silver_record

    async def test_transform_bronze_to_silver_partial_record(
        self,
        pubchem_config,
        pubchem_runtime,
        mock_pubchem_services,
    ):
        """Тест трансформации неполной записи."""
        pipeline = PubChemCompoundPipeline(
            config=pubchem_config,
            runtime=pubchem_runtime,
            services=mock_pubchem_services,
        )

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_pubchem_services.logger,
        )

        # Partial record - only CID and molecular_weight
        bronze_record = {
            "cid": 123456,
            "molecular_weight": 250.5,
        }

        silver_record = await pipeline.transform_bronze_to_silver(context, bronze_record)

        assert silver_record is not None
        assert silver_record["cid"] == "123456"  # Now string
        assert silver_record["molecular_weight"] == 250.5
        assert silver_record["molecular_formula"] is None
        assert silver_record["canonical_smiles"] is None
        assert "entity_id" in silver_record
        assert "content_hash" in silver_record

    async def test_transform_bronze_to_silver_missing_cid_returns_none(
        self,
        pubchem_config,
        pubchem_runtime,
        mock_pubchem_services,
    ):
        """Тест: запись без CID возвращает None."""
        pipeline = PubChemCompoundPipeline(
            config=pubchem_config,
            runtime=pubchem_runtime,
            services=mock_pubchem_services,
        )

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_pubchem_services.logger,
        )

        bronze_record = {"molecular_weight": 100.0}  # No CID

        silver_record = await pipeline.transform_bronze_to_silver(context, bronze_record)

        assert silver_record is None

    async def test_extract_watermark(
        self,
        pubchem_config,
        pubchem_runtime,
        mock_pubchem_services,
    ):
        """Тест извлечения watermark из записи."""
        pipeline = PubChemCompoundPipeline(
            config=pubchem_config,
            runtime=pubchem_runtime,
            services=mock_pubchem_services,
        )

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_pubchem_services.logger,
        )

        record = {"cid": 54321, "molecular_weight": 100.0}
        watermark = pipeline.extract_watermark(context, record)

        assert watermark == 54321

    async def test_extract_watermark_missing_cid(
        self,
        pubchem_config,
        pubchem_runtime,
        mock_pubchem_services,
    ):
        """Тест извлечения watermark при отсутствии CID."""
        pipeline = PubChemCompoundPipeline(
            config=pubchem_config,
            runtime=pubchem_runtime,
            services=mock_pubchem_services,
        )

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_pubchem_services.logger,
        )

        record = {"molecular_weight": 100.0}  # No CID
        watermark = pipeline.extract_watermark(context, record)

        assert watermark == 0


@pytest.mark.integration
class TestPubChemCompoundPipelineCreate:
    """Тесты создания PubChem пайплайна."""

    def test_create_pipeline(
        self,
        pubchem_config,
        pubchem_runtime,
        mock_pubchem_services,
    ):
        """Тест создания пайплайна через factory method."""
        pipeline = PubChemCompoundPipeline.create(
            runtime=pubchem_runtime,
            services=mock_pubchem_services,
            config=pubchem_config,
        )

        assert pipeline is not None
        assert isinstance(pipeline, PubChemCompoundPipeline)
        assert pipeline.config == pubchem_config
