"""Integration tests for the UniProt Protein pipeline.

Тестирует E2E трансформации и интеграцию с инфраструктурой.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.application.pipelines.uniprot import UniProtProteinPipeline
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer
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
def uniprot_config() -> PipelineConfig:
    """Создаёт конфигурацию UniProt пайплайна."""
    return PipelineConfig(
        pipeline_name="uniprot_protein",
        provider="uniprot",
        entity_type="protein",
        table=TableConfig(
            primary_keys=["accession"],
            silver_table="uniprot.protein",
            gold_table="uniprot.protein_gold",
        ),
        batch_size=100,
        checkpoint_interval=1000,
        fields=[
            "accession",
            "entry_name",
            "protein_name",
            "gene_primary",
            "taxonomy_id",
            "sequence_length",
        ],
    )


@pytest.fixture
def uniprot_runtime() -> RuntimeConfig:
    """Создаёт runtime конфигурацию."""
    return RuntimeConfig(
        run_type=RunType.INCREMENTAL,
        resume=False,
        limit=None,
    )


@pytest.fixture
def mock_uniprot_services(mock_logger) -> PipelineService:
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
class TestUniProtProteinPipelineTransform:
    """Тесты трансформации UniProt пайплайна."""

    async def test_pipeline_transform__complete_record__78f6dc57(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест трансформации полной записи Bronze → Silver."""
        run_id = deterministic_uuid("uniprot.complete.pipeline")
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=instantiate_test_transformer(
                UniProtProteinTransformer,
                provider="uniprot",
            ),
        )

        context = PipelineContext(
            run_id=deterministic_uuid("uniprot.complete.context"),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        # Full UniProt record structure
        bronze_record = {
            "primaryAccession": "P12345",
            "uniProtkbId": "MYC_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Myc proto-oncogene protein"}}
            },
            "genes": [
                {"geneName": {"value": "MYC"}},
                {"geneName": {"value": "BHLHE39"}},
            ],
            "organism": {"taxonId": 9606},
            "sequence": {"length": 439, "value": "MDFFRVVENQQPPATMPLNVSFTNRNYDLDYD..."},
        }

        silver_record = await pipeline.transform_bronze_to_silver(
            context, bronze_record
        )

        assert silver_record is not None
        assert silver_record["accession"] == "P12345"
        assert silver_record["entry_name"] == "MYC_HUMAN"
        assert silver_record["protein_name"] == "Myc proto-oncogene protein"
        assert silver_record["gene_primary"] == "MYC"
        assert silver_record["taxonomy_id"] == 9606
        assert "gene_names" not in silver_record
        assert "organism_id" not in silver_record
        assert silver_record["sequence_length"] == 439
        assert "entity_id" in silver_record
        assert "content_hash" in silver_record
        assert "_run_id" in silver_record

    async def test_transform_bronze_to_silver_minimal_record(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест трансформации минимальной записи с обязательными полями.

        Protein entity requires: accession, entry_name.
        Optional fields: protein_name, gene_primary, taxonomy_id, sequence_length.
        """
        run_id = deterministic_uuid("uniprot.minimal.pipeline")
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=instantiate_test_transformer(
                UniProtProteinTransformer,
                provider="uniprot",
            ),
        )

        context = PipelineContext(
            run_id=deterministic_uuid("uniprot.minimal.context"),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        # Minimal valid record with only required fields (accession, entry_name)
        bronze_record = {
            "primaryAccession": "Q99999",
            "uniProtkbId": "TEST_HUMAN",
            # No proteinDescription - protein_name will be None
        }

        silver_record = await pipeline.transform_bronze_to_silver(
            context, bronze_record
        )

        assert silver_record is not None
        assert silver_record["accession"] == "Q99999"
        assert silver_record["entry_name"] == "TEST_HUMAN"
        assert silver_record["protein_name"] is None
        assert silver_record["gene_primary"] is None
        assert silver_record["taxonomy_id"] is None
        assert "gene_names" not in silver_record
        assert "organism_id" not in silver_record
        assert silver_record["sequence_length"] is None
        assert "entity_id" in silver_record
        assert "content_hash" in silver_record
        assert "_run_id" in silver_record

    async def test_transform_bronze_to_silver_missing_accession_returns_none(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест: запись без primaryAccession возвращает None."""
        run_id = deterministic_uuid("uniprot.missing_accession.pipeline")
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=instantiate_test_transformer(
                UniProtProteinTransformer,
                provider="uniprot",
            ),
        )

        context = PipelineContext(
            run_id=deterministic_uuid("uniprot.missing_accession.context"),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        bronze_record = {"uniProtkbId": "NO_ACCESSION"}  # No primaryAccession

        silver_record = await pipeline.transform_bronze_to_silver(
            context, bronze_record
        )

        assert silver_record is None

    async def test_transform_bronze_to_silver_missing_protein_description_accepted(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест: запись без proteinDescription успешно обрабатывается.

        protein_name is optional, so records without
        proteinDescription.recommendedName.fullName.value are accepted.
        """
        run_id = deterministic_uuid("uniprot.missing_description.pipeline")
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=instantiate_test_transformer(
                UniProtProteinTransformer,
                provider="uniprot",
            ),
        )

        context = PipelineContext(
            run_id=deterministic_uuid("uniprot.missing_description.context"),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        bronze_record = {
            "primaryAccession": "A0A000",
            "uniProtkbId": "UNKNOWN_HUMAN",
            "genes": [{"geneName": {"value": "GENE1"}}],
            "organism": {"taxonId": 9606},
            "sequence": {"length": 100},
            # Missing: proteinDescription - this is OK, protein_name is optional
        }

        silver_record = await pipeline.transform_bronze_to_silver(
            context, bronze_record
        )

        assert silver_record is not None
        assert silver_record["accession"] == "A0A000"
        assert silver_record["protein_name"] is None
        assert silver_record["gene_primary"] == "GENE1"
        assert "gene_names" not in silver_record
        assert "entity_id" in silver_record
        assert "_run_id" in silver_record

    async def test_transform_bronze_to_silver_empty_genes(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест трансформации записи с пустым списком генов."""
        run_id = deterministic_uuid("uniprot.empty_genes.pipeline")
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=instantiate_test_transformer(
                UniProtProteinTransformer,
                provider="uniprot",
            ),
        )

        context = PipelineContext(
            run_id=deterministic_uuid("uniprot.empty_genes.context"),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        bronze_record = {
            "primaryAccession": "B0B000",
            "uniProtkbId": "NOGENE_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "No Gene Protein"}}
            },
            "genes": [],
        }

        silver_record = await pipeline.transform_bronze_to_silver(
            context, bronze_record
        )

        assert silver_record is not None
        assert silver_record["gene_primary"] is None
        assert "gene_names" not in silver_record
        assert "_run_id" in silver_record

    async def test_transform_extracts_new_fields(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Test extraction of taxonomy, GO, PTM, isoform, and reaction fields."""
        run_id = deterministic_uuid("uniprot.new_fields.pipeline")
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=instantiate_test_transformer(
                UniProtProteinTransformer,
                provider="uniprot",
            ),
        )

        context = PipelineContext(
            run_id=deterministic_uuid("uniprot.new_fields.context"),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        # Full record with all new field types
        bronze_record = {
            "primaryAccession": "P00533",
            "uniProtkbId": "EGFR_HUMAN",
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "Epidermal growth factor receptor"}
                }
            },
            "organism": {
                "taxonId": 9606,
                "scientificName": "Homo sapiens",
                "lineage": [
                    "Eukaryota",
                    "Metazoa",
                    "Chordata",
                    "Mammalia",
                    "Primates",
                    "Hominidae",
                    "Homo",
                ],
            },
            "sequence": {"length": 1210, "value": "MRPSGTAGAALLALLAALCPA..."},
            "uniProtKBCrossReferences": [
                {
                    "database": "GO",
                    "id": "GO:0005524",
                    "properties": [
                        {"key": "GoTerm", "value": "F:ATP binding"},
                        {"key": "GoEvidenceType", "value": "IEA"},
                    ],
                },
                {
                    "database": "GO",
                    "id": "GO:0005886",
                    "properties": [
                        {"key": "GoTerm", "value": "C:plasma membrane"},
                        {"key": "GoEvidenceType", "value": "TAS"},
                    ],
                },
            ],
            "features": [
                {
                    "type": "Topological domain",
                    "description": "Extracellular",
                    "location": {"start": {"value": 25}, "end": {"value": 645}},
                },
                {
                    "type": "Transmembrane",
                    "description": "Helical",
                    "location": {"start": {"value": 646}, "end": {"value": 668}},
                },
                {
                    "type": "Signal peptide",
                    "description": "Signal",
                    "location": {"start": {"value": 1}, "end": {"value": 24}},
                },
                {
                    "type": "Glycosylation",
                    "description": "N-linked (GlcNAc...)",
                    "location": {"start": {"value": 56}, "end": {"value": 56}},
                },
                {
                    "type": "Disulfide bond",
                    "description": "Disulfide",
                    "location": {"start": {"value": 271}, "end": {"value": 283}},
                },
                {
                    "type": "Modified residue",
                    "description": "Phosphotyrosine",
                    "featureId": "PTM-001",
                    "location": {"start": {"value": 1068}, "end": {"value": 1068}},
                },
                {
                    "type": "Modified residue",
                    "description": "N-acetylalanine",
                    "featureId": "PTM-002",
                    "location": {"start": {"value": 1}, "end": {"value": 1}},
                },
            ],
            "comments": [
                {
                    "commentType": "ALTERNATIVE PRODUCTS",
                    "isoforms": [
                        {
                            "isoformIds": ["P00533-1", "P00533-2"],
                            "name": {"value": "Isoform 1"},
                            "synonyms": [{"value": "EGFRvIII"}],
                        },
                    ],
                },
                {
                    "commentType": "CATALYTIC ACTIVITY",
                    "reaction": {
                        "name": "ATP + L-tyrosyl-[protein] = ADP + H(+) + O-phospho-L-tyrosyl-[protein]",
                        "ecNumber": "2.7.10.1",
                    },
                },
            ],
        }

        silver_record = await pipeline.transform_bronze_to_silver(
            context, bronze_record
        )

        assert silver_record is not None

        # Taxonomy components
        assert "superkingdom" in silver_record
        assert silver_record["superkingdom"] == "Eukaryota"
        assert "phylum" in silver_record
        assert silver_record["phylum"] == "Metazoa"
        assert "genus" in silver_record
        assert silver_record["genus"] == "Hominidae"

        # GO components
        assert "molecular_function" in silver_record
        assert silver_record["molecular_function"] is not None
        assert "ATP binding" in silver_record["molecular_function"]
        assert "cellular_component" in silver_record
        assert silver_record["cellular_component"] is not None
        assert "plasma membrane" in silver_record["cellular_component"]

        # Structural features
        assert "topology" in silver_record
        assert silver_record["topology"] is not None
        assert "transmembrane" in silver_record
        assert silver_record["transmembrane"] is not None
        assert "intramembrane" in silver_record  # None expected
        assert "signal_peptide" in silver_record
        assert silver_record["signal_peptide"] is not None
        assert "propeptide" in silver_record  # None expected

        # PTM features
        assert "glycosylation" in silver_record
        assert silver_record["glycosylation"] is not None
        assert "lipidation" in silver_record  # None expected
        assert "disulfide_bond" in silver_record
        assert silver_record["disulfide_bond"] is not None
        assert "modified_residue" in silver_record
        assert silver_record["modified_residue"] is not None
        assert "phosphorylation" in silver_record
        assert silver_record["phosphorylation"] is not None
        assert "Phosphotyrosine" in silver_record["phosphorylation"]
        assert "acetylation" in silver_record
        assert silver_record["acetylation"] is not None
        assert "acetylalanine" in silver_record["acetylation"]
        assert "ubiquitination" in silver_record  # None expected

        # Isoform details
        assert "isoform_names" in silver_record
        assert silver_record["isoform_names"] is not None
        assert "Isoform 1" in silver_record["isoform_names"]
        assert "isoform_ids" in silver_record
        assert silver_record["isoform_ids"] is not None
        assert "P00533-1" in silver_record["isoform_ids"]
        assert "isoform_synonyms" in silver_record
        assert silver_record["isoform_synonyms"] is not None
        assert "EGFRvIII" in silver_record["isoform_synonyms"]

        # Reaction data
        assert "reactions" in silver_record
        assert silver_record["reactions"] is not None
        assert "ATP" in silver_record["reactions"]
        assert "reaction_ec_numbers" in silver_record
        assert silver_record["reaction_ec_numbers"] is not None
        assert "2.7.10.1" in silver_record["reaction_ec_numbers"]


@pytest.mark.integration
class TestUniProtProteinPipelineCreate:
    """Тесты создания UniProt пайплайна."""

    def test_create_pipeline__test_uni_prot_protein_pipeline_create_tests_integration_test_uniprot_pipeline_561(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест создания пайплайна через factory method."""
        run_id = deterministic_uuid("uniprot.create.pipeline")
        pipeline = UniProtProteinPipeline.create(
            run_id=run_id,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
            config=uniprot_config,
            shutdown_signal=ShutdownSignal(),
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
        run_id = deterministic_uuid("uniprot.malformed_genes.pipeline")
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=instantiate_test_transformer(
                UniProtProteinTransformer,
                provider="uniprot",
            ),
        )

        context = PipelineContext(
            run_id=deterministic_uuid("uniprot.malformed_genes.context"),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        # Malformed genes - some missing geneName
        bronze_record = {
            "primaryAccession": "X00001",
            "uniProtkbId": "MALFORM_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "Malformed Genes Protein"}}
            },
            "genes": [
                {"geneName": {"value": "VALID"}},
                {"otherField": "no geneName"},
                {"geneName": {}},  # Empty geneName
            ],
        }

        silver_record = await pipeline.transform_bronze_to_silver(
            context, bronze_record
        )

        assert silver_record is not None
        # Should only include valid gene names
        assert silver_record["gene_primary"] == "VALID"
        assert "gene_names" not in silver_record
        assert "_run_id" in silver_record

    async def test_transform_with_none_organism(
        self,
        uniprot_config,
        uniprot_runtime,
        mock_uniprot_services,
    ):
        """Тест трансформации с None organism."""
        run_id = deterministic_uuid("uniprot.none_organism.pipeline")
        pipeline = UniProtProteinPipeline(
            config=uniprot_config,
            runtime=uniprot_runtime,
            services=mock_uniprot_services,
            run_id=run_id,
            shutdown_signal=ShutdownSignal(),
            transformer=instantiate_test_transformer(
                UniProtProteinTransformer,
                provider="uniprot",
            ),
        )

        context = PipelineContext(
            run_id=deterministic_uuid("uniprot.none_organism.context"),
            run_type=RunType.INCREMENTAL,
            logger=mock_uniprot_services.logger,
        )

        bronze_record = {
            "primaryAccession": "Y00001",
            "uniProtkbId": "NOORG_HUMAN",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "No Organism Protein"}}
            },
            "organism": None,
        }

        silver_record = await pipeline.transform_bronze_to_silver(
            context, bronze_record
        )

        assert silver_record is not None
        assert silver_record["taxonomy_id"] is None
        assert "organism_id" not in silver_record
        assert "_run_id" in silver_record
