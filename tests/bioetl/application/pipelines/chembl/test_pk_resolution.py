import pytest
from unittest.mock import MagicMock
from bioetl.application.pipelines.chembl.pipeline import ChemblEntityPipeline
from bioetl.infrastructure.config.models import PipelineConfig, ChemblSourceConfig

@pytest.fixture
def dependencies():
    return {
        "logger": MagicMock(),
        "validation_service": MagicMock(),
        "output_writer": MagicMock(),
        "extraction_service": MagicMock(),
        "hash_service": MagicMock(),
    }

def test_pk_resolution_from_field(dependencies):
    """Test that primary_key is picked up from the config field."""
    config = PipelineConfig(
        id="chembl.test_entity",
        provider="chembl",
        entity="test_entity",
        primary_key="custom_pk_id",
        input_mode="auto_detect",
        input_path=None,
        output_path="/tmp/out",
        batch_size=10,
        provider_config=ChemblSourceConfig(
            base_url="https://www.ebi.ac.uk/chembl/api/data",
            timeout_sec=30,
            max_retries=3,
            rate_limit_per_sec=10.0,
        ),
    )
    
    pipeline = ChemblEntityPipeline(config=config, **dependencies)
    assert pipeline.ID_COLUMN == "custom_pk_id"
    assert pipeline.API_FILTER_KEY == "custom_pk_id__in"

def test_pk_resolution_from_pipeline_dict(dependencies):
    """Test fallback to pipeline dict for legacy configs."""
    config = PipelineConfig(
        id="chembl.test_entity",
        provider="chembl",
        entity="test_entity",
        primary_key=None,
        pipeline={"primary_key": "legacy_pk_id"},
        input_mode="auto_detect",
        input_path=None,
        output_path="/tmp/out",
        batch_size=10,
        provider_config=ChemblSourceConfig(
            base_url="https://www.ebi.ac.uk/chembl/api/data",
            timeout_sec=30,
            max_retries=3,
            rate_limit_per_sec=10.0,
        ),
    )
    
    pipeline = ChemblEntityPipeline(config=config, **dependencies)
    assert pipeline.ID_COLUMN == "legacy_pk_id"
    assert pipeline.API_FILTER_KEY == "legacy_pk_id__in"

def test_pk_resolution_default(dependencies):
    """Test fallback to entity_name_id."""
    config = PipelineConfig(
        id="chembl.my_entity",
        provider="chembl",
        entity="my_entity",
        primary_key=None,
        input_mode="auto_detect",
        input_path=None,
        output_path="/tmp/out",
        batch_size=10,
        provider_config=ChemblSourceConfig(
            base_url="https://www.ebi.ac.uk/chembl/api/data",
            timeout_sec=30,
            max_retries=3,
            rate_limit_per_sec=10.0,
        ),
    )
    
    pipeline = ChemblEntityPipeline(config=config, **dependencies)
    assert pipeline.ID_COLUMN == "my_entity_id"
    assert pipeline.API_FILTER_KEY == "my_entity_id__in"

