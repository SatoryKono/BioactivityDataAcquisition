"""Compose provider health and actual resolved Medallion destinations."""

from __future__ import annotations

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
