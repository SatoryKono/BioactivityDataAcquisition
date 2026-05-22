"""DQ Context Resolver.

Consolidated DQ config/path extraction and DQ services creation.
Merges pipeline_factory_dq_helpers.py + DQ methods from BaseServicesFactory.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, cast

from bioetl.composition.bootstrap_contexts import DQConfigsContext, DQOutputPathsContext
from bioetl.composition.factories.dq._context_resolver_support import (
    create_dq_services_impl,
    extract_dq_configs_impl,
    extract_dq_output_paths_impl,
    extract_single_dq_config_impl,
    get_flat_structure_impl,
    get_layer_path_impl,
    get_output_root_impl,
    has_flat_structure_impl,
    is_dq_report_enabled_impl,
)
from bioetl.composition.factories.dq.factory import DQServicesFactory

if TYPE_CHECKING:
    from pydantic import BaseModel

    from bioetl.domain.ports import (
        BronzeDQAnalyzerPort,
        BronzeDQConfigPort,
        DQReportWriterPort,
        GoldDQAnalyzerPort,
        GoldDQConfigPort,
        LoggerPort,
        MetricsPort,
        SilverDQAnalyzerPort,
        SilverDQConfigPort,
    )
    from bioetl.domain.types import JsonDict
    from bioetl.infrastructure.config._base import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "create_dq_services",
    "extract_dq_configs",
    "extract_dq_output_paths",
    "extract_single_dq_config",
    "get_flat_structure",
    "get_layer_path",
    "get_output_root",
    "has_flat_structure",
    "is_dq_report_enabled",
]


# ---- Single-layer DQ config extraction ----


def extract_single_dq_config(
    sink: Mapping[str, object],
    layer_name: str,
    config_class: type[BaseModel],
) -> BronzeDQConfigPort | SilverDQConfigPort | GoldDQConfigPort | None:
    """Extract enabled DQ config for one layer."""
    return extract_single_dq_config_impl(sink, layer_name, config_class)


# ---- Multi-layer DQ config extraction ----


def extract_dq_configs(yaml_config: PipelineYamlConfig | None) -> DQConfigsContext:
    """Extract bronze/silver/gold DQ configs from YAML."""
    return extract_dq_configs_impl(
        yaml_config,
        extract_single_dq_config_fn=extract_single_dq_config,
    )


# ---- Path/structure helpers ----


def get_layer_path(config: object) -> str | None:
    """Extract path from a layer config when present."""
    return get_layer_path_impl(config)


def has_flat_structure(config: object) -> bool:
    """Return ``True`` when layer config enables flat structure."""
    return has_flat_structure_impl(config)


def extract_dq_output_paths(
    yaml_config: PipelineYamlConfig | None,
) -> DQOutputPathsContext:
    """Extract per-layer DQ output paths and flat-structure mode."""
    return extract_dq_output_paths_impl(
        yaml_config,
        get_layer_path_fn=get_layer_path,
        has_flat_structure_fn=has_flat_structure,
    )


# ---- DQ service enablement queries ----


def is_dq_report_enabled(config: PipelineYamlConfig) -> bool:
    """Return ``True`` when any layer enables DQ reporting."""
    return is_dq_report_enabled_impl(config)


def get_flat_structure(config: PipelineYamlConfig) -> bool:
    """Return ``True`` when any DQ sink uses flat structure."""
    return get_flat_structure_impl(config)


def get_output_root(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
) -> Path:
    """Resolve the output root for DQ report emission."""
    return get_output_root_impl(settings, pipeline_config)


def _create_dq_report_service(
    *,
    logger: LoggerPort,
    bronze_analyzer: object,
    silver_analyzer: object,
    gold_analyzer: object,
    report_writer: object,
    metrics: MetricsPort | None,
) -> object:
    """Bridge the DQ report service constructor to the factory protocol."""
    from bioetl.application.services.dq_report_service import DQReportService

    return DQReportService(
        logger=logger,
        bronze_analyzer=cast("BronzeDQAnalyzerPort | None", bronze_analyzer),
        silver_analyzer=cast("SilverDQAnalyzerPort | None", silver_analyzer),
        gold_analyzer=cast("GoldDQAnalyzerPort | None", gold_analyzer),
        report_writer=cast("DQReportWriterPort | None", report_writer),
        metrics=metrics,
    )


# ---- DQ services factory ----


def create_dq_services(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    metrics: MetricsPort | None = None,
) -> JsonDict:  # Any: heterogeneous DQ service instances
    """Create DQ analyzers, report writer, and report service."""
    return create_dq_services_impl(
        settings,
        pipeline_config,
        logger,
        metrics=metrics,
        create_bronze_analyzer_fn=DQServicesFactory.create_bronze_analyzer,
        create_silver_analyzer_fn=DQServicesFactory.create_silver_analyzer,
        create_gold_analyzer_fn=DQServicesFactory.create_gold_analyzer,
        create_report_writer_fn=DQServicesFactory.create_report_writer,
        dq_report_service_cls=_create_dq_report_service,
        is_dq_report_enabled_fn=is_dq_report_enabled,
        get_output_root_fn=get_output_root,
        get_flat_structure_fn=get_flat_structure,
    )
