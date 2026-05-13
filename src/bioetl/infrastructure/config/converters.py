"""Configuration schema-to-domain conversion utilities.

This module centralizes conversion orchestration from validated infrastructure
schema models to domain configuration objects.
"""

from __future__ import annotations

__all__ = ["dq_overrides_to_domain", "yaml_config_to_domain"]

from typing import Literal

from bioetl.domain.composite.config import ColumnGroupConfig
from bioetl.domain.config import (
    DQConfig,
    FieldPolicyConfig,
    PipelineConfig,
    TableConfig,
)
from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
from bioetl.domain.medallion import GoldWriteMode, SilverWriteMode
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _extract_source_fields(yaml_config: PipelineYamlConfig) -> list[str]:
    """Extract field names from source config.

    Returns:
        List of field name strings extracted from the source configuration.
    """
    source_fields = yaml_config.source.fields
    if not source_fields:
        return []
    if isinstance(source_fields[0], dict):
        return [field["name"] for field in source_fields if "name" in field]
    return [str(field) for field in source_fields]


def _extract_write_modes(
    yaml_config: PipelineYamlConfig,
) -> tuple[SilverWriteMode, GoldWriteMode]:
    """Extract and convert write modes from sink config to domain enums.

    Returns:
        Tuple of (SilverWriteMode enum, GoldWriteMode enum) from the sink config.
    """
    silver_config = yaml_config.sink.get("silver")
    gold_config = yaml_config.sink.get("gold")

    silver_mode = SilverWriteMode.MERGE
    if silver_config and silver_config.mode:
        silver_mode = SilverWriteMode.from_string(silver_config.mode)

    gold_mode = GoldWriteMode.SCD2
    if gold_config and gold_config.mode:
        gold_mode = GoldWriteMode.from_string(gold_config.mode)

    return silver_mode, gold_mode


def _build_silver_filters(yaml_config: PipelineYamlConfig) -> SilverFilterConfig:
    """Build structural Silver layer filter config from YAML config.

    Returns:
        SilverFilterConfig instance built from the YAML filter configuration.
    """
    return yaml_config.silver_filters.to_domain()


def _build_gold_filters(yaml_config: PipelineYamlConfig) -> GoldFilterConfig:
    """Build GoldFilterConfig from YAML config.

    Returns:
        GoldFilterConfig instance built from the YAML filter configuration.
    """
    return yaml_config.gold_filters.to_domain()


def dq_overrides_to_domain(yaml_config: PipelineYamlConfig) -> DQConfig:
    """Convert inline DQ overrides from YAML config to domain DQConfig.

    Args:
        yaml_config: Configuration for yaml.

    Returns:
        The DQConfig result.
    """
    return yaml_config.dq_overrides.to_domain()


def _build_field_policy(
    yaml_config: PipelineYamlConfig,
) -> tuple[FieldPolicyConfig, ...]:
    """Build explicit field-level policy overrides from YAML config."""

    def _normalize_boolean_vocabulary(values: list[str]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            token = value.strip().lower()
            if not token or token in seen:
                continue
            seen.add(token)
            normalized.append(token)
        return tuple(normalized)

    return tuple(
        FieldPolicyConfig(
            field=field_name,
            optional=policy.optional,
            empty_as_missing=policy.empty_as_missing,
            coercion_policy=policy.coercion_policy,
            boolean_true_values=_normalize_boolean_vocabulary(
                policy.boolean_true_values
            ),
            boolean_false_values=_normalize_boolean_vocabulary(
                policy.boolean_false_values
            ),
        )
        for field_name, policy in sorted(yaml_config.field_policy.items())
    )


def yaml_config_to_domain(
    yaml_config: PipelineYamlConfig,
    resolved_dq_config: DQConfig | None = None,
) -> PipelineConfig:
    """Map validated YAML schema config to immutable domain PipelineConfig.

    Returns:
        PipelineConfig instance with fully resolved domain configuration.
    """
    source_fields = _extract_source_fields(yaml_config)
    write_mode, gold_write_mode = _extract_write_modes(yaml_config)
    silver_filters = _build_silver_filters(yaml_config)
    gold_filters = _build_gold_filters(yaml_config)
    silver_sink = yaml_config.sink.get("silver")
    on_schema_mismatch: Literal["error", "evolve", "ignore"] = (
        silver_sink.on_schema_mismatch if silver_sink else "error"
    )
    dq_config = resolved_dq_config or dq_overrides_to_domain(yaml_config)
    transform_version = yaml_config.transform.version
    transform_steps = tuple(yaml_config.transform.steps)
    field_policy = _build_field_policy(yaml_config)
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
    scd_config = (
        gold_config.scd_config.to_domain(
            primary_keys=tuple(yaml_config.business_primary_keys or ())
        )
        if gold_config and gold_config.scd_config is not None
        else None
    )

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
        field_policy=field_policy,
        dq=dq_config,
        transform_version=transform_version,
        transform_steps=transform_steps,
        loading_strategy=yaml_config.loading_strategy,
        scd_config=scd_config,
    )
