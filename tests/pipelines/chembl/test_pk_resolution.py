import pytest
from unittest.mock import MagicMock
from bioetl.application.pipelines.chembl.pipeline import ChemblEntityPipeline
from bioetl.infrastructure.config.models import PipelineConfig

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
        provider="chembl",
        entity_name="test_entity",
        primary_key="custom_pk_id"
    )
    
    pipeline = ChemblEntityPipeline(config=config, **dependencies)
    assert pipeline.ID_COLUMN == "custom_pk_id"
    assert pipeline.API_FILTER_KEY == "custom_pk_id__in"

def test_pk_resolution_from_pipeline_dict(dependencies):
    """Test fallback to pipeline dict for legacy configs."""
    config = PipelineConfig(
        provider="chembl",
        entity_name="test_entity",
        # primary_key is None by default
        pipeline={"primary_key": "legacy_pk_id"}
    )
    
    pipeline = ChemblEntityPipeline(config=config, **dependencies)
    assert pipeline.ID_COLUMN == "legacy_pk_id"
    assert pipeline.API_FILTER_KEY == "legacy_pk_id__in"

def test_pk_resolution_default(dependencies):
    """Test fallback to entity_name_id."""
    config = PipelineConfig(
        provider="chembl",
        entity_name="my_entity",
        # No primary_key anywhere
    )
    
    pipeline = ChemblEntityPipeline(config=config, **dependencies)
    assert pipeline.ID_COLUMN == "my_entity_id"
    assert pipeline.API_FILTER_KEY == "my_entity_id__in"

