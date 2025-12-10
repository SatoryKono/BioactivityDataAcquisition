from unittest.mock import MagicMock

import pytest

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.domain.configs import (
    ChemblSourceConfig,
    ClientConfig,
    PipelineConfig,
)


@pytest.fixture
def dependencies():
    record_source = MagicMock()
    record_source.iter_records.return_value = iter([])

    return {
        "logger": MagicMock(),
        "validation_service": MagicMock(),
        "loader": MagicMock(),
        "extraction_service": MagicMock(),
        "hash_service": MagicMock(),
        "normalization_service": MagicMock(),
        "record_source": record_source,
    }


def test_pk_resolution_from_field_config(dependencies):
    """Test that primary_key is picked up from the config field (config module)."""
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
            client=ClientConfig(
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            ),
        ),
    )

    pipeline = ChemblPipelineBase(config=config, **dependencies)
    assert pipeline.ID_COLUMN == "custom_pk_id"
    assert pipeline.API_FILTER_KEY == "custom_pk_id__in"


def test_pk_resolution_from_identity_primary_key_list_config(dependencies):
    """Test resolution from identity.primary_key list (config module)."""
    config = PipelineConfig(
        id="chembl.test_entity",
        provider="chembl",
        entity="test_entity",
        primary_key=["my_pk_id", "secondary_pk"],  # Uses first element
        input_mode="auto_detect",
        input_path=None,
        output_path="/tmp/out",
        batch_size=10,
        provider_config=ChemblSourceConfig(
            base_url="https://www.ebi.ac.uk/chembl/api/data",
            client=ClientConfig(
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            ),
        ),
    )

    pipeline = ChemblPipelineBase(config=config, **dependencies)
    assert pipeline.ID_COLUMN == "my_pk_id"
    assert pipeline.API_FILTER_KEY == "my_pk_id__in"


def test_pk_resolution_default_config(dependencies):
    """Test fallback to entity_name_id (config module)."""
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
            client=ClientConfig(
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            ),
        ),
    )

    pipeline = ChemblPipelineBase(config=config, **dependencies)
    assert pipeline.ID_COLUMN == "my_entity_id"
    assert pipeline.API_FILTER_KEY == "my_entity_id__in"
