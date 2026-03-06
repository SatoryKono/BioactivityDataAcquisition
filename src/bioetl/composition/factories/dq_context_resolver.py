"""DQ Context Resolver.

Consolidated DQ config/path extraction and DQ services creation.
Merges pipeline_factory_dq_helpers.py + DQ methods from BaseServicesFactory.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.composition.bootstrap_contexts import DQConfigsContext, DQOutputPathsContext
from bioetl.composition.factories.dq_factory import DQServicesFactory

if TYPE_CHECKING:
    from pydantic import BaseModel

    from bioetl.domain.ports import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        LoggerPort,
        SilverDQConfigPort,
    )
    from bioetl.domain.types import JsonDict
    from bioetl.infrastructure.config import Settings
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


class _ModelDumpable(Protocol):
    """Protocol for Pydantic-like models exposing model_dump()."""

    def model_dump(self) -> dict[str, object]:
        """Serialize model to dictionary."""
        ...


# ---- Single-layer DQ config extraction ----


def extract_single_dq_config(
    sink: Mapping[str, object],
    layer_name: str,
    config_class: type[BaseModel],
) -> BronzeDQConfigPort | SilverDQConfigPort | GoldDQConfigPort | None:
    """Extract DQ config for a single layer.

    Returns:
        Enabled DQ config for the layer, or None if absent or disabled.
    """
    sink_config = sink.get(layer_name)
    if not sink_config:
        return None

    if not hasattr(sink_config, "model_dump"):
        return None

    dumpable = cast(_ModelDumpable, sink_config)
    validated = config_class.model_validate(dumpable.model_dump())
    dq_report = getattr(validated, "dq_report", None)
    if dq_report is not None and getattr(dq_report, "enabled", False):
        return cast(
            "BronzeDQConfigPort | SilverDQConfigPort | GoldDQConfigPort",
            dq_report,
        )
    return None


# ---- Multi-layer DQ config extraction ----


def extract_dq_configs(yaml_config: PipelineYamlConfig | None) -> DQConfigsContext:
    """Extract DQ report configs from YAML.

    Returns:
        DQConfigsContext with bronze, silver, and gold DQ configs.
    """
    from bioetl.infrastructure.schemas.dq_report_config import (
        BronzeSinkConfig,
        GoldSinkConfig,
        SilverSinkConfig,
    )

    if yaml_config is None:
        return DQConfigsContext(bronze=None, silver=None, gold=None)

    sink = getattr(yaml_config, "sink", None)
    if sink is None or not isinstance(sink, Mapping):
        return DQConfigsContext(bronze=None, silver=None, gold=None)

    sink_mapping = cast(Mapping[str, object], sink)
    bronze_config = cast(
        "BronzeDQConfigPort | None",
        extract_single_dq_config(sink_mapping, "bronze", BronzeSinkConfig),
    )
    silver_config = cast(
        "SilverDQConfigPort | None",
        extract_single_dq_config(sink_mapping, "silver", SilverSinkConfig),
    )
    gold_config = cast(
        "GoldDQConfigPort | None",
        extract_single_dq_config(sink_mapping, "gold", GoldSinkConfig),
    )

    return DQConfigsContext(
        bronze=bronze_config,
        silver=silver_config,
        gold=gold_config,
    )


# ---- Path/structure helpers ----


def get_layer_path(config: object) -> str | None:
    """Extract path from layer config if available.

    Returns:
        Path string from config, or None if config is absent or has no path.
    """
    return getattr(config, "path", None) if config else None


def has_flat_structure(config: object) -> bool:
    """Check if layer config has flat_structure enabled.

    Returns:
        True if flat_structure is set on the config, False otherwise.
    """
    return bool(config and getattr(config, "flat_structure", False))


def extract_dq_output_paths(
    yaml_config: PipelineYamlConfig | None,
) -> DQOutputPathsContext:
    """Extract DQ output paths and flat_structure from YAML config.

    Returns:
        DQOutputPathsContext with per-layer paths and flat_structure flag.
    """
    if yaml_config is None:
        return DQOutputPathsContext(
            bronze_path=None,
            silver_path=None,
            gold_path=None,
            flat_structure=False,
        )

    sink = getattr(yaml_config, "sink", None)
    if sink is None or not isinstance(sink, Mapping):
        return DQOutputPathsContext(
            bronze_path=None,
            silver_path=None,
            gold_path=None,
            flat_structure=False,
        )

    sink_mapping = cast(Mapping[str, object], sink)
    bronze_config = sink_mapping.get("bronze")
    silver_config = sink_mapping.get("silver")
    gold_config = sink_mapping.get("gold")

    flat = has_flat_structure(silver_config) or has_flat_structure(gold_config)

    return DQOutputPathsContext(
        bronze_path=get_layer_path(bronze_config),
        silver_path=get_layer_path(silver_config),
        gold_path=get_layer_path(gold_config),
        flat_structure=flat,
    )


# ---- DQ service enablement queries ----


def is_dq_report_enabled(config: PipelineYamlConfig) -> bool:
    """Check if any DQ report is enabled in pipeline config.

    Args:
        config: Pipeline YAML configuration.

    Returns:
        True if any layer has dq_report.enabled = true.
    """
    sink = config.sink
    for layer_name in ("bronze", "silver", "gold"):
        layer_config = sink.get(layer_name)
        if layer_config and layer_config.dq_report.enabled:
            return True
    return False


def get_flat_structure(config: PipelineYamlConfig) -> bool:
    """Get flat_structure setting from pipeline config.

    Checks Silver and Gold layers for flat_structure setting.
    Returns True if either layer has flat_structure enabled.

    Args:
        config: Pipeline YAML configuration.

    Returns:
        True if flat_structure is enabled for any layer.
    """
    sink = config.sink
    for layer_name in ("silver", "gold"):
        layer_config = sink.get(layer_name)
        if layer_config and getattr(layer_config, "flat_structure", False):
            return True
    return False


def get_output_root(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
) -> Path:
    """Derive output root from pipeline config or fall back to settings.

    DQ reports should be written alongside the data. This method extracts
    the output root from the bronze sink path configuration when available.

    Args:
        settings: Application settings.
        pipeline_config: Pipeline YAML configuration.

    Returns:
        Path to the output root directory.
    """
    bronze_config = pipeline_config.sink.get("bronze")

    if not settings.test_mode and bronze_config and bronze_config.path:
        bronze_path = Path(bronze_config.path)
        # Go up 3 levels: bronze/provider/entity -> output root
        return bronze_path.parent.parent.parent

    return settings.data_dir


# ---- DQ services factory ----


def create_dq_services(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
) -> JsonDict:  # Any: heterogeneous DQ service instances
    """Create DQ analyzers/writer/services when DQ reporting is enabled.

    Returns:
        Dict of DQ service instances keyed by role, or empty dict if DQ disabled.
    """
    dq_enabled = is_dq_report_enabled(pipeline_config)

    if not dq_enabled:
        return {}

    bronze_analyzer = DQServicesFactory.create_bronze_analyzer()
    silver_analyzer = DQServicesFactory.create_silver_analyzer()
    gold_analyzer = DQServicesFactory.create_gold_analyzer()

    output_root = get_output_root(settings, pipeline_config)
    dq_reports_path = output_root / "reports" / "dq"
    flat_structure = get_flat_structure(pipeline_config)
    report_writer = DQServicesFactory.create_report_writer(
        base_path=dq_reports_path,
        logger=logger,
        flat_structure=flat_structure,
    )

    from bioetl.application.services.dq_report_service import DQReportService

    report_service = DQReportService(
        logger=logger,
        bronze_analyzer=bronze_analyzer,
        silver_analyzer=silver_analyzer,
        gold_analyzer=gold_analyzer,
        report_writer=report_writer,
    )

    return {
        "bronze_analyzer": bronze_analyzer,
        "silver_analyzer": silver_analyzer,
        "gold_analyzer": gold_analyzer,
        "report_writer": report_writer,
        "report_service": report_service,
    }
