"""Integration tests for the PubChem Compound pipeline.

Тестирует E2E трансформации и интеграцию с инфраструктурой.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.application.pipelines.pubchem import PubChemCompoundPipeline
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer
from bioetl.domain.config import PipelineConfig, RuntimeConfig, TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.locking import FencingToken
from bioetl.domain.types import RunType
from tests.helpers.deterministic_ids import deterministic_uuid
from tests.helpers.transformer_dependencies import instantiate_test_transformer

_MOCK_TOKEN = FencingToken(
    sequence=1,
    key="lock:mock",
    owner_id=UUID("00000000-0000-0000-0000-000000000000"),
    issued_at=0.0,
)


@pytest.fixture
def pubchem_config() -> PipelineConfig:
    """Создаёт конфигурацию PubChem пайплайна."""
    return PipelineConfig(
        pipeline_name="pubchem_compound",
        provider="pubchem",
        entity_type="compound",
        table=TableConfig(
            primary_keys=["molecule_id"],
            silver_table="pubchem.compound",
            gold_table="pubchem.compound_gold",
        ),
        batch_size=100,
        checkpoint_interval=1000,
        fields=[
            "molecule_id",
            "molecular_formula",
            "molecular_weight",
            "canonical_smiles",
            "isomeric_smiles",
            "inchi",
            "inchi_key",
            "iupac_name",
        ],
    )


@pytest.fixture
def pubchem_runtime() -> RuntimeConfig:
    """Создаёт runtime конфигурацию."""
    return RuntimeConfig(
        run_type=RunType.INCREMENTAL,
        resume=False,
        limit=None,
    )


@pytest.fixture
def mock_pubchem_services(mock_logger) -> PipelineService:
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
    mock_lock.acquire = AsyncMock(return_value=_MOCK_TOKEN)
    mock_lock.release = AsyncMock()

    mock_checkpoint = AsyncMock()
    mock_checkpoint.get_latest = AsyncMock(return_value=None)
    mock_checkpoint.save = AsyncMock()

    mock_quarantine = AsyncMock()
    mock_metrics = MagicMock()

    import structlog

    logger = structlog.get_logger()

    mock_tracing = MagicMock()

    return PipelineService(
        data_source=mock_data_source,
        storage=mock_storage,
        lock=mock_lock,
        checkpoint=mock_checkpoint,
        quarantine=mock_quarantine,
        metrics=mock_metrics,
        tracing=mock_tracing,
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
        run_id = deterministic_uuid("pubchem.complete.pipeline")
        pipeline = PubChemCompoundPipeline(
            config=pubchem_config,
            runtime=pubchem_runtime,
            services=mock_pubchem_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=instantiate_test_transformer(
                PubChemCompoundTransformer,
                provider="pubchem",
            ),
        )

        context = PipelineContext(
            run_id=deterministic_uuid("pubchem.complete.context"),
            run_type=RunType.INCREMENTAL,
            logger=mock_pubchem_services.logger,
        )

        bronze_record = {
            "molecule_id": 2244,
            "molecular_formula": "C9H8O4",
            "molecular_weight": 180.16,
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "isomeric_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
            "inchi_key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            "iupac_name": "2-acetyloxybenzoic amolecule_id",
        }

        silver_record = await pipeline.transform_bronze_to_silver(
            context, bronze_record
        )

        assert silver_record is not None
        assert silver_record["molecule_id"] == "2244"  # Now string
        assert silver_record["molecular_formula"] == "C9H8O4"
        assert silver_record["molecular_weight"] == pytest.approx(
            180.16
        )  # Now stored as float
        assert silver_record["canonical_smiles"] == "CC(=O)OC1=CC=CC=C1C(=O)O"
        assert silver_record["inchi_key"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
        assert silver_record["iupac_name"] == "2-acetyloxybenzoic amolecule_id"
        assert "entity_id" in silver_record
        assert "content_hash" in silver_record
        assert "_run_id" in silver_record

    async def test_transform_bronze_to_silver_partial_record(
        self,
        pubchem_config,
        pubchem_runtime,
        mock_pubchem_services,
    ):
        """Тест трансформации неполной записи.

        Note: Compound entity requires at least one structural identifier
        (canonical_smiles, isomeric_smiles, or inchi). Records without
        structural identifiers are rejected per entity invariant.
        """
        run_id = deterministic_uuid("pubchem.partial.pipeline")
        pipeline = PubChemCompoundPipeline(
            config=pubchem_config,
            runtime=pubchem_runtime,
            services=mock_pubchem_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=instantiate_test_transformer(
                PubChemCompoundTransformer,
                provider="pubchem",
            ),
        )

        context = PipelineContext(
            run_id=deterministic_uuid("pubchem.partial.context"),
            run_type=RunType.INCREMENTAL,
            logger=mock_pubchem_services.logger,
        )

        # Partial record - CID, molecular_weight and one structural identifier
        bronze_record = {
            "molecule_id": 123456,
            "molecular_weight": 250.5,
            "canonical_smiles": "CCCC",  # Required: at least one structural ID
        }

        silver_record = await pipeline.transform_bronze_to_silver(
            context, bronze_record
        )

        assert silver_record is not None
        assert silver_record["molecule_id"] == "123456"  # Now string
        assert silver_record["molecular_weight"] == pytest.approx(
            250.5
        )  # Now stored as float
        assert silver_record["molecular_formula"] is None
        assert silver_record["canonical_smiles"] == "CCCC"
        assert "entity_id" in silver_record
        assert "content_hash" in silver_record
        assert "_run_id" in silver_record

    async def test_transform_bronze_to_silver_no_structural_id_returns_none(
        self,
        pubchem_config,
        pubchem_runtime,
        mock_pubchem_services,
    ):
        """Тест: запись без структурных идентификаторов возвращает None.

        Compound entity invariant requires at least one of:
        canonical_smiles, isomeric_smiles, or inchi.
        """
        run_id = deterministic_uuid("pubchem.no_structural_id.pipeline")
        pipeline = PubChemCompoundPipeline(
            config=pubchem_config,
            runtime=pubchem_runtime,
            services=mock_pubchem_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=instantiate_test_transformer(
                PubChemCompoundTransformer,
                provider="pubchem",
            ),
        )

        context = PipelineContext(
            run_id=deterministic_uuid("pubchem.no_structural_id.context"),
            run_type=RunType.INCREMENTAL,
            logger=mock_pubchem_services.logger,
        )

        # Record without any structural identifiers
        bronze_record = {
            "molecule_id": 123456,
            "molecular_weight": 250.5,
        }

        silver_record = await pipeline.transform_bronze_to_silver(
            context, bronze_record
        )

        assert silver_record is None

    async def test_transform_bronze_to_silver_missing_molecule_id_returns_none(
        self,
        pubchem_config,
        pubchem_runtime,
        mock_pubchem_services,
    ):
        """Тест: запись без CID возвращает None."""
        run_id = deterministic_uuid("pubchem.missing_molecule_id.pipeline")
        pipeline = PubChemCompoundPipeline(
            config=pubchem_config,
            runtime=pubchem_runtime,
            services=mock_pubchem_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=instantiate_test_transformer(
                PubChemCompoundTransformer,
                provider="pubchem",
            ),
        )

        context = PipelineContext(
            run_id=deterministic_uuid("pubchem.missing_molecule_id.context"),
            run_type=RunType.INCREMENTAL,
            logger=mock_pubchem_services.logger,
        )

        bronze_record = {"molecular_weight": 100.0}  # No CID

        silver_record = await pipeline.transform_bronze_to_silver(
            context, bronze_record
        )

        assert silver_record is None


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
        run_id = deterministic_uuid("pubchem.create.pipeline")
        pipeline = PubChemCompoundPipeline.create(
            run_id=run_id,
            runtime=pubchem_runtime,
            services=mock_pubchem_services,
            config=pubchem_config,
            shutdown_signal=ShutdownSignal(),
        )

        assert pipeline is not None
        assert isinstance(pipeline, PubChemCompoundPipeline)
        assert pipeline.config == pubchem_config
