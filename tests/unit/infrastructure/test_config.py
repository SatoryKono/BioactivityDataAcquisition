"""Unit tests for configuration mapping."""

from bioetl.domain.config import PipelineConfig
from bioetl.infrastructure.config import yaml_config_to_domain
from bioetl.infrastructure.schemas.pipeline_config import DQConfig as YamlDQConfig
from bioetl.infrastructure.schemas.pipeline_config import (
    PipelineYamlConfig,
    SinkLayerConfig,
)


def test_yaml_config_to_domain_mapping():
    """Test mapping from YAML schema to Domain config."""
    yaml_config = PipelineYamlConfig(
        pipeline_name="test_pipeline",
        provider="test",
        entity_type="entity",
        primary_keys=["id"],
        silver_table="silver.test",
        dq_rules=YamlDQConfig(),
        sink={"silver": SinkLayerConfig(mode="append")},
    )

    domain_config = yaml_config_to_domain(yaml_config)

    assert isinstance(domain_config, PipelineConfig)
    assert domain_config.pipeline_name == "test_pipeline"
    assert domain_config.write_mode == "append"
    # Table config verification
    assert domain_config.table.silver_write_mode == "append"
    assert domain_config.table.silver_table == "silver.test"


def test_yaml_config_to_domain_default_mode():
    """Test default write mode is merge."""
    yaml_config = PipelineYamlConfig(
        pipeline_name="test_pipeline",
        provider="test",
        entity_type="entity",
        primary_keys=["id"],
        silver_table="silver.test",
        dq_rules=YamlDQConfig(),
    )

    domain_config = yaml_config_to_domain(yaml_config)

    assert domain_config.write_mode == "merge"
