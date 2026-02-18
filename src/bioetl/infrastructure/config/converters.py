"""Configuration schema-to-domain conversion utilities.

This module centralizes conversion orchestration from validated infrastructure
schema models to domain configuration objects.
"""

from __future__ import annotations

from typing import Literal

from bioetl.domain.composite.config import ColumnGroupConfig
from bioetl.domain.config import DQConfig, PipelineConfig, TableConfig
from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _extract_source_fields(yaml_config: PipelineYamlConfig) -> list[str]:
    """Extract field names from source config."""
    source_fields = yaml_config.source.fields
    if source_fields and isinstance(source_fields[0], dict):
        return [field["name"] for field in source_fields if "name" in field]
    return source_fields  # type: ignore[return-value]


def _extract_write_modes(
    yaml_config: PipelineYamlConfig,
) -> tuple[SilverWriteMode, GoldWriteMode]:
    """Extract and convert write modes from sink config to domain enums."""
    silver_config = yaml_config.sink.get("silver")
    gold_config = yaml_config.sink.get("gold")

    silver_mode = SilverWriteMode.MERGE
    if silver_config and silver_config.mode:
        silver_mode = SilverWriteMode.from_string(silver_config.mode)

    gold_mode = GoldWriteMode.APPEND
    if gold_config and gold_config.mode:
        gold_mode = GoldWriteMode.from_string(gold_config.mode)

    return silver_mode, gold_mode


def _build_silver_filters(yaml_config: PipelineYamlConfig) -> SilverFilterConfig:
    """Build Silver layer filter config from YAML config."""
    base_filters = yaml_config.silver_filters.to_domain()
    return SilverFilterConfig.from_base(base_filters)


def _build_gold_filters(yaml_config: PipelineYamlConfig) -> GoldFilterConfig:
    """Build GoldFilterConfig from YAML config."""
    return yaml_config.gold_filters.to_domain()


def dq_overrides_to_domain(yaml_config: PipelineYamlConfig) -> DQConfig:
    """Convert inline DQ overrides from YAML config to domain DQConfig."""
    return yaml_config.dq_overrides.to_domain()


def yaml_config_to_domain(
    yaml_config: PipelineYamlConfig,
    resolved_dq_config: DQConfig | None = None,
) -> PipelineConfig:
    """Map PipelineYamlConfig to domain PipelineConfig."""
    source_fields = _extract_source_fields(yaml_config)
    write_mode, gold_write_mode = _extract_write_modes(yaml_config)
    silver_filters = _build_silver_filters(yaml_config)
    gold_filters = _build_gold_filters(yaml_config)

    on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error"
    if yaml_config.sink:
        silver_sink = yaml_config.sink.get("silver")
        if silver_sink:
            on_schema_mismatch = silver_sink.on_schema_mismatch

    dq_config = resolved_dq_config or dq_overrides_to_domain(yaml_config)

    transform_version = yaml_config.transform.version
    transform_steps = tuple(yaml_config.transform.steps)
    column_groups = tuple(
        ColumnGroupConfig(**group.model_dump()) for group in yaml_config.column_groups
    )

    table = TableConfig(
        primary_keys=tuple(yaml_config.business_primary_keys or ()),
        silver_table=yaml_config.silver_table,
        gold_table=yaml_config.gold_table,
        silver_write_mode=write_mode,
        gold_write_mode=gold_write_mode,
        on_schema_mismatch=on_schema_mismatch,
    )

    gold_config = yaml_config.sink.get("gold")
    scd_config = gold_config.scd_config if gold_config else None

    return PipelineConfig(
        pipeline_name=yaml_config.pipeline_name,
        provider=yaml_config.provider,
        entity_type=yaml_config.entity_type,
        table=table,
        silver_filters=silver_filters,
        gold_filters=gold_filters,
        batch_size=yaml_config.batch_size,
        checkpoint_interval=yaml_config.checkpoint_interval,
        fields=tuple(source_fields),
        column_groups=column_groups,
        dq=dq_config,
        transform_version=transform_version,
        transform_steps=transform_steps,
        loading_strategy=yaml_config.loading_strategy,
        scd_config=scd_config,
    )
