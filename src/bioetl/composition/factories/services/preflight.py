"""Compose provider health and actual resolved Medallion destinations."""

from __future__ import annotations

from functools import partial
from pathlib import Path

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.preflight import (
    HealthAggregator,
    MedallionConfigValidator,
    PreflightService,
)
from bioetl.application.core.preflight.medallion_validator import PreflightLayerConfig
from bioetl.domain.medallion import WriteModePolicy
from bioetl.domain.ports import HealthMonitorPort, LoggerPort
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.time import SystemClock
from bioetl.composition.bootstrap.assembly.target_classification_runtime import (
    validate_target_runtime_dependency,
)
from bioetl.infrastructure.storage.target_classification_guard import (
    assert_target_table_compatibility,
)


def _resolves_table_path(value: object) -> bool:
    return callable(getattr(value, "_resolve_table_path", None))


def _table_path(writer: object, table_name: str) -> str:
    resolver_name = "_resolve_table_path"
    return str(getattr(writer, resolver_name)(table_name))


def build_preflight_service(
    *,
    pipeline: BasePipeline,
    logger: LoggerPort,
    yaml_config: PipelineYamlConfig | None,
    health_monitor: HealthMonitorPort,
) -> PreflightService:
    """Build startup validation without importing another factory's private modules."""
    return PreflightService(
        config=pipeline.config,
        context=pipeline.context,
        logger=logger,
        metrics=pipeline.services.metrics,
        health_aggregator=HealthAggregator(
            logger=logger,
            health_monitor=health_monitor,
            health_check_mode=pipeline.runtime.health_check_mode,
            clock=SystemClock(),
        ),
        medallion_validator=MedallionConfigValidator(
            config=pipeline.config,
            logger=logger,
            write_mode_policy=WriteModePolicy(),
        ),
        layer_config=_build_preflight_layer_config(
            pipeline.services.storage, yaml_config
        ),
        dependency_validator=(
            partial(_validate_target_dependencies, pipeline, yaml_config)
            if yaml_config is not None
            and pipeline.config.pipeline_name == "chembl_target"
            else None
        ),
    )


def _validate_target_dependencies(
    pipeline: BasePipeline, config: PipelineYamlConfig
) -> None:
    validate_target_runtime_dependency(
        config, exact_replay=bool(getattr(pipeline.runtime, "exact_replay", False))
    )
    if pipeline.runtime.dry_run:
        return
    storage = pipeline.services.storage
    silver = getattr(storage, "silver", None)
    gold = getattr(storage, "gold", None)
    if not _resolves_table_path(silver) or not _resolves_table_path(gold):
        raise TypeError(
            "target preflight requires actual Silver and Gold table path resolvers"
        )
    assert_target_table_compatibility(
        silver_path=Path(_table_path(silver, pipeline.config.effective_silver_table)),
        gold_path=Path(_table_path(gold, pipeline.config.effective_gold_table)),
        mode=config.target_classification.mode,
        destructive=pipeline.runtime.run_type.value in {"backfill", "rebuild"},
        table_contract=config.target_classification.to_domain().contract_version,
    )


def _build_preflight_layer_config(
    storage: object, yaml_config: PipelineYamlConfig | None
) -> PreflightLayerConfig:
    """Bind preflight to actual writer destinations, including YAML defaulted paths."""
    sink = yaml_config.sink if yaml_config is not None else {}
    silver, gold = sink.get("silver"), sink.get("gold")
    bronze_writer = getattr(storage, "bronze", None)
    silver_writer = getattr(storage, "silver", None)
    gold_writer = getattr(storage, "gold", None)
    return PreflightLayerConfig(
        bronze_path=str(bronze_writer.base_path) if bronze_writer is not None else None,
        silver_path=str(silver_writer.base_path) if silver_writer is not None else None,
        gold_path=str(gold_writer.base_path) if gold_writer is not None else None,
        silver_format=silver.format if silver is not None else None,
        gold_format=gold.format if gold is not None else None,
    )
