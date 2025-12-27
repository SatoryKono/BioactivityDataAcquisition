"""Configuration mappers for converting infrastructure schemas to domain objects.

Transfers responsibility of mapping from Infrastructure layer to Composition layer.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.config import PipelineConfig
from bioetl.domain.filter_config import (
    GoldColumnFilter,
    GoldFilterConfig,
    GoldListContainsFilter,
    GoldListLengthFilter,
    GoldRangeFilter,
)
from bioetl.infrastructure.config import load_pipeline_config
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _extract_source_fields(yaml_config: PipelineYamlConfig) -> list[str]:
    """Extract field names from source config."""
    source_fields = yaml_config.source.fields
    if source_fields and isinstance(source_fields[0], dict):
        return [field["name"] for field in source_fields if "name" in field]
    return source_fields  # type: ignore[return-value]


def _extract_write_modes(yaml_config: PipelineYamlConfig) -> tuple[str, str]:
    """Extract write modes from sink config."""
    silver_config = yaml_config.sink.get("silver")
    gold_config = yaml_config.sink.get("gold")

    write_mode = silver_config.mode if silver_config and silver_config.mode else "merge"
    gold_write_mode = gold_config.mode if gold_config and gold_config.mode else "append"

    return write_mode, gold_write_mode


def _build_gold_filters(yaml_config: PipelineYamlConfig) -> GoldFilterConfig:
    """Build GoldFilterConfig from YAML config."""
    gf = yaml_config.gold_filters
    return GoldFilterConfig(
        column_filters=tuple(
            GoldColumnFilter(column=col, values=frozenset(vals))
            for col, vals in gf.columns.items()
        ),
        range_filters=tuple(
            GoldRangeFilter(
                column=col,
                min_value=r.min,
                max_value=r.max,
                include_min=r.include_min,
                include_max=r.include_max,
            )
            for col, r in gf.ranges.items()
        ),
        list_length_filters=tuple(
            GoldListLengthFilter(column=col, min_length=r.min, max_length=r.max)
            for col, r in gf.list_lengths.items()
        ),
        list_contains_filters=tuple(
            GoldListContainsFilter(column=col, values=frozenset(r.values), mode=r.mode)
            for col, r in gf.list_contains.items()
        ),
        required_fields=tuple(gf.required_fields),
        exclude_if_present=tuple(gf.exclude_if_present),
    )


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
    source_fields = _extract_source_fields(yaml_config)
    write_mode, gold_write_mode = _extract_write_modes(yaml_config)
    gold_filters = _build_gold_filters(yaml_config)

    # Extract on_schema_mismatch from silver sink config
    on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error"
    if yaml_config.sink:
        silver_sink = yaml_config.sink.get("silver")
        if silver_sink:
            on_schema_mismatch = silver_sink.on_schema_mismatch

    return PipelineConfig(
        pipeline_name=yaml_config.pipeline_name,
        provider=yaml_config.provider,
        entity_type=yaml_config.entity_type,
        primary_keys=yaml_config.primary_keys,
        silver_table=yaml_config.silver_table,
        gold_table=yaml_config.gold_table,
        write_mode=write_mode,
        gold_write_mode=gold_write_mode,
        gold_filters=gold_filters,
        batch_size=yaml_config.batch_size,
        checkpoint_interval=yaml_config.checkpoint_interval,
        fields=source_fields,
        dq=DomainDQConfig(
            soft_fail_threshold=yaml_config.dq_rules.soft_fail_threshold,
            hard_fail_threshold=yaml_config.dq_rules.hard_fail_threshold,
        ),
        on_schema_mismatch=on_schema_mismatch,
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
