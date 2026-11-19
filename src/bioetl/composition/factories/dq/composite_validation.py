"""Composition factory for composite validation services."""

from __future__ import annotations

from bioetl.domain.behavior.aggregation_validator import AggregationValidator
from bioetl.domain.behavior.composite_validation_layer import CompositeValidator
from bioetl.domain.behavior.cross_validation_validator import CrossValidationValidator
from bioetl.domain.behavior.preflight_governance import PreflightGovernor


def create_composite_validation_service() -> CompositeValidator:
    """Create the default composite validation service wiring."""
    return CompositeValidator(
        aggregation_validator=AggregationValidator(),
        cross_validation_validator=CrossValidationValidator(),
        preflight_governance=PreflightGovernor(),
    )


from pathlib import Path

from bioetl.composition.factories.storage.factory import (
    get_layer_configs,
    resolve_delta_writer_base_path,
    resolve_delta_writer_flat_structure,
    resolve_flat_structure_flags,
    resolve_storage_paths,
)
from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.storage.delta.table_ops import resolve_delta_table_path


def resolve_target_table_paths(
    settings: Settings, config: PipelineYamlConfig
) -> tuple[Path, Path]:
    """Resolve both physical Delta tables without constructing or opening writers."""
    bronze, silver, gold = get_layer_configs(config)
    use_yaml, _, silver_path, gold_path = resolve_storage_paths(
        settings=settings,
        bronze_config=bronze,
        silver_config=silver,
        gold_config=gold,
    )
    _, silver_flat, gold_flat = resolve_flat_structure_flags(
        bronze_config=bronze,
        silver_config=silver,
        gold_config=gold,
        use_yaml_paths=use_yaml,
    )
    domain = yaml_config_to_domain(config)
    return (
        _physical_path(silver_path, silver_flat, domain.effective_silver_table, config),
        _physical_path(gold_path, gold_flat, domain.effective_gold_table, config),
    )


def _physical_path(
    path: Path, flat: bool, table_name: str, config: PipelineYamlConfig
) -> Path:
    flat = resolve_delta_writer_flat_structure(
        path,
        provider=config.provider,
        entity_type=config.entity_type,
        flat_structure=flat,
    )
    base = resolve_delta_writer_base_path(
        path,
        provider=config.provider,
        entity_type=config.entity_type,
        flat_structure=flat,
    )
    return Path(
        resolve_delta_table_path(
            base_path=str(base), table_name=table_name, flat_structure=flat
        )
    )
