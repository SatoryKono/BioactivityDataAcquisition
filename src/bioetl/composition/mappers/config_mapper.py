"""Mappers for converting configuration schemas to domain objects."""

from functools import lru_cache

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.config import PipelineConfig
from bioetl.infrastructure.config import load_pipeline_config
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def yaml_config_to_domain(yaml_config: PipelineYamlConfig) -> PipelineConfig:
    """Map PipelineYamlConfig to domain PipelineConfig.

    This is the boundary mapping function that converts validated infrastructure
    schema to domain model. All validation has already been done by Pydantic
    in PipelineYamlConfig.

    Args:
        yaml_config: Validated PipelineYamlConfig from infrastructure layer

    Returns:
        PipelineConfig: Immutable domain configuration
    """
    # Extract field names from source config
    source_fields = yaml_config.source.fields
    if source_fields and isinstance(source_fields[0], dict):
        # Handle cases where fields are dicts like [{'name': 'col1'}, ...]
        source_fields = [field["name"] for field in source_fields if "name" in field]

    watermark_field = yaml_config.source.watermark_field

    return PipelineConfig(
        pipeline_name=yaml_config.pipeline_name,
        provider=yaml_config.provider,
        entity_type=yaml_config.entity_type,
        primary_keys=yaml_config.primary_keys,
        silver_table=yaml_config.silver_table,
        gold_table=yaml_config.gold_table,
        gold_filter_types=yaml_config.gold_filter_types,
        batch_size=yaml_config.batch_size,
        checkpoint_interval=yaml_config.checkpoint_interval,
        fields=source_fields,
        watermark_field=watermark_field,
        dq=DomainDQConfig(
            soft_fail_threshold=yaml_config.dq_rules.soft_fail_threshold,
            hard_fail_threshold=yaml_config.dq_rules.hard_fail_threshold,
        ),
    )


@lru_cache(maxsize=10)
def get_pipeline_config(pipeline_name: str) -> PipelineConfig:
    """Get PipelineConfig object from YAML configuration.

    Convenience function that loads and maps config in one step.
    Results are cached for efficiency.

    Args:
        pipeline_name: Name of the pipeline (e.g., 'chembl_activity')

    Returns:
        PipelineConfig instance

    Raises:
        ValueError: If pipeline configuration not found
    """
    yaml_config = load_pipeline_config(pipeline_name)
    return yaml_config_to_domain(yaml_config)

__all__ = ["get_pipeline_config", "yaml_config_to_domain"]
