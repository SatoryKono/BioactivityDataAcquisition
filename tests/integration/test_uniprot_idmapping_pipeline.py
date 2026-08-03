# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Integration tests for the UniProt ID-mapping pipeline runtime path."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.application.pipelines.generic import GenericPipeline
from bioetl.application.pipelines.uniprot.idmapping_transformer import (
    IDMappingTransformer,
)
from bioetl.domain.config import PipelineConfig, RuntimeConfig, TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.locking import FencingToken
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import instantiate_test_transformer

_MOCK_TOKEN = FencingToken(
    sequence=1,
    key="lock:mock",
    owner_id=UUID("00000000-0000-0000-0000-000000000000"),
    issued_at=0.0,
)


@pytest.fixture
def idmapping_config() -> PipelineConfig:
    """Create configuration for the UniProt ID-mapping pipeline."""
    return PipelineConfig(
        pipeline_name="uniprot_idmapping",
        provider="uniprot",
        entity_type="idmapping",
        table=TableConfig(
            primary_keys=["target_id"],
            silver_table="uniprot.idmapping",
            gold_table="uniprot.idmapping_gold",
        ),
        batch_size=100,
        checkpoint_interval=1000,
        fields=[
            "target_id",
            "uniprot_accession",
            "mapping_status",
            "taxonomy_id",
            "all_mappings",
            "protein_name",
        ],
    )


@pytest.fixture
def idmapping_runtime() -> RuntimeConfig:
    """Create runtime configuration."""
    return RuntimeConfig(
        run_type=RunType.INCREMENTAL,
        resume=False,
        limit=None,
    )


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


@pytest.fixture
def mock_idmapping_services(mock_logger) -> PipelineService:
    """Create mock services for pipeline integration tests."""
    mock_data_source = AsyncMock()
    mock_data_source.provider_name = "uniprot_idmapping"
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
    mock_tracing = MagicMock()

    import structlog

    logger = structlog.get_logger()

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


@pytest.mark.integration
class TestUniProtIDMappingPipelineTransform:
    """Runtime-path integration tests for UniProt ID mapping."""

    async def test_transform_bronze_to_silver_found_mapping_canonicalizes_taxonomy(
        self,
        idmapping_config,
        idmapping_runtime,
        mock_idmapping_services,
    ) -> None:
        """Found mappings should emit canonical chained-enrichment anchors."""
        pipeline = GenericPipeline(
            config=idmapping_config,
            runtime=idmapping_runtime,
            services=mock_idmapping_services,
            run_id=deterministic_uuid_from_callsite("test_uniprot_idmapping_pipeline"),
            shutdown_signal=ShutdownSignal(),
            transformer=instantiate_test_transformer(
                IDMappingTransformer,
                provider="uniprot",
                entity_type="idmapping",
            ),
        )

        context = PipelineContext(
            run_id=deterministic_uuid_from_callsite("test_uniprot_idmapping_pipeline"),
            run_type=RunType.INCREMENTAL,
            logger=mock_idmapping_services.logger,
        )
        bronze_record = {
            "target_id": " chembl204 ",
            "uniprot_accession": " p00742 ",
            "taxonomy_id": " 09606 ",
            "protein_name": " Example Protein ",
            "reviewed": True,
        }

        silver_record = await pipeline.transform_bronze_to_silver(
            context, bronze_record
        )

        assert silver_record is not None
        assert silver_record["target_id"] == "CHEMBL204"
        assert silver_record["uniprot_accession"] == "P00742"
        assert silver_record["taxonomy_id"] == 9606
        assert silver_record["mapping_status"] == "found"
        assert silver_record["_dq_warn"] is False
        assert silver_record["entity_id"] == "uniprot:CHEMBL204"
        assert "content_hash" in silver_record

    async def test_transform_bronze_to_silver_multiple_mapping_normalizes_identifier_set(
        self,
        idmapping_config,
        idmapping_runtime,
        mock_idmapping_services,
    ) -> None:
        """Multiple mappings should keep canonical mixed-identifier payloads."""
        pipeline = GenericPipeline(
            config=idmapping_config,
            runtime=idmapping_runtime,
            services=mock_idmapping_services,
            run_id=deterministic_uuid_from_callsite("test_uniprot_idmapping_pipeline"),
            shutdown_signal=ShutdownSignal(),
            transformer=instantiate_test_transformer(
                IDMappingTransformer,
                provider="uniprot",
                entity_type="idmapping",
            ),
        )

        context = PipelineContext(
            run_id=deterministic_uuid_from_callsite("test_uniprot_idmapping_pipeline"),
            run_type=RunType.INCREMENTAL,
            logger=mock_idmapping_services.logger,
        )
        bronze_record = {
            "target_id": "CHEMBL204",
            "uniprot_accession": "P00742",
            "all_mappings": ["q9y6k9", " p00742 ", "CHEMBL204"],
            "taxonomy_id": "9606",
        }

        silver_record = await pipeline.transform_bronze_to_silver(
            context, bronze_record
        )

        assert silver_record is not None
        assert silver_record["mapping_status"] == "multiple"
        assert silver_record["taxonomy_id"] == 9606
        assert silver_record["all_mappings"] == '["CHEMBL204","P00742","Q9Y6K9"]'
        assert silver_record["_dq_warn"] is False

    async def test_transform_bronze_to_silver_not_found_mapping_sets_dq_warn(
        self,
        idmapping_config,
        idmapping_runtime,
        mock_idmapping_services,
    ) -> None:
        """Not-found mappings should remain valid Silver rows with warning flag."""
        pipeline = GenericPipeline(
            config=idmapping_config,
            runtime=idmapping_runtime,
            services=mock_idmapping_services,
            run_id=deterministic_uuid_from_callsite("test_uniprot_idmapping_pipeline"),
            shutdown_signal=ShutdownSignal(),
            transformer=instantiate_test_transformer(
                IDMappingTransformer,
                provider="uniprot",
                entity_type="idmapping",
            ),
        )

        context = PipelineContext(
            run_id=deterministic_uuid_from_callsite("test_uniprot_idmapping_pipeline"),
            run_type=RunType.INCREMENTAL,
            logger=mock_idmapping_services.logger,
        )
        bronze_record = {
            "target_id": "CHEMBL9999999999",
            "uniprot_accession": None,
            "taxonomy_id": "10090",
        }

        silver_record = await pipeline.transform_bronze_to_silver(
            context, bronze_record
        )

        assert silver_record is not None
        assert silver_record["target_id"] == "CHEMBL9999999999"
        assert silver_record["uniprot_accession"] is None
        assert silver_record["taxonomy_id"] == 10090
        assert silver_record["mapping_status"] == "not_found"
        assert silver_record["_dq_warn"] is True
