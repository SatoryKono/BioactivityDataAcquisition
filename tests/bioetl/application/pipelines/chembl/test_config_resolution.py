from unittest.mock import MagicMock

import pytest

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.domain.configs import (
    DataFlowConfig,
    DataSinkConfig,
    DataSourceConfig,
    PipelineConfig,
    PipelineIdentityConfig,
)
from bioetl.domain.configs.pipeline import ChemblSourceConfig, ProviderHttpConfig
from bioetl.infrastructure.chembl.model_registry import get_chembl_model_registry


@pytest.fixture
def dependencies():
    # ExtractStage uses extraction_service.iter_extract instead of record_source
    extraction_service = MagicMock()
    extraction_service.iter_extract.return_value = iter([])

    return {
        "logger": MagicMock(),
        "validation_service": MagicMock(),
        "loader": MagicMock(),
        "extraction_service": extraction_service,
        "hash_service": MagicMock(),
        "normalization_service": MagicMock(),
        "index_generator": MagicMock(),
        "entity_model_registry": get_chembl_model_registry(),
        "timestamp_provider": MagicMock(),
        "entity_model_registry": get_chembl_model_registry(),
    }


def test_pk_resolution_from_field_config(dependencies):
    """Test that primary_key is picked up from the config field (config module)."""
    config = PipelineConfig(
        identity=PipelineIdentityConfig(
            pipeline_id="chembl.test_entity",
            provider="chembl",
            entity="test_entity",
            primary_key=["custom_pk_id"],
        ),
        data_flow=DataFlowConfig(
            source=DataSourceConfig(
                input_mode="auto_detect",
                input_path=None,
                batch_size=10,
            ),
            sink=DataSinkConfig(output_path="C:/tmp/out"),
        ),
        provider_config=ChemblSourceConfig(
            http=ProviderHttpConfig(
                base_url="https://www.ebi.ac.uk/chembl/api/data",
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            )
        ),
    )

    pipeline = ChemblPipelineBase(config=config, **dependencies)
    assert pipeline.ID_COLUMN == "custom_pk_id"
    assert pipeline.API_FILTER_KEY == "custom_pk_id__in"


def test_pk_resolution_from_identity_primary_key_list_config(dependencies):
    """Test resolution from identity.primary_key list (config module)."""
    config = PipelineConfig(
        identity=PipelineIdentityConfig(
            pipeline_id="chembl.test_entity",
            provider="chembl",
            entity="test_entity",
            primary_key=["my_pk_id", "secondary_pk"],
        ),
        data_flow=DataFlowConfig(
            source=DataSourceConfig(
                input_mode="auto_detect",
                input_path=None,
                batch_size=10,
            ),
            sink=DataSinkConfig(output_path="C:/tmp/out"),
        ),
        provider_config=ChemblSourceConfig(
            http=ProviderHttpConfig(
                base_url="https://www.ebi.ac.uk/chembl/api/data",
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            )
        ),
    )

    pipeline = ChemblPipelineBase(config=config, **dependencies)
    assert pipeline.ID_COLUMN == "my_pk_id"
    assert pipeline.API_FILTER_KEY == "my_pk_id__in"


def test_pk_resolution_default_config(dependencies):
    """Test fallback to entity_name_id (config module)."""
    config = PipelineConfig(
        identity=PipelineIdentityConfig(
            pipeline_id="chembl.my_entity",
            provider="chembl",
            entity="my_entity",
            primary_key=[],
        ),
        data_flow=DataFlowConfig(
            source=DataSourceConfig(
                input_mode="auto_detect",
                input_path=None,
                batch_size=10,
            ),
            sink=DataSinkConfig(output_path="C:/tmp/out"),
        ),
        provider_config=ChemblSourceConfig(
            http=ProviderHttpConfig(
                base_url="https://www.ebi.ac.uk/chembl/api/data",
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            )
        ),
    )

    pipeline = ChemblPipelineBase(config=config, **dependencies)
    assert pipeline.ID_COLUMN == "my_entity_id"
    assert pipeline.API_FILTER_KEY == "my_entity_id__in"
