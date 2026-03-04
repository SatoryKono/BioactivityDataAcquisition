"""DQ config/path extraction helpers for pipeline factory."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.composition.bootstrap_contexts import DQConfigsContext, DQOutputPathsContext

if TYPE_CHECKING:
    from pydantic import BaseModel

    from bioetl.domain.ports import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        SilverDQConfigPort,
    )
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class _ModelDumpable(Protocol):
    """Protocol for Pydantic-like models exposing model_dump()."""

    def model_dump(self) -> dict[str, object]:
        """Serialize model to dictionary."""
        ...


def extract_single_dq_config(
    sink: Mapping[str, object],
    layer_name: str,
    config_class: type[BaseModel],
) -> BronzeDQConfigPort | SilverDQConfigPort | GoldDQConfigPort | None:
    """Extract DQ config for a single layer."""
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


def extract_dq_configs(yaml_config: PipelineYamlConfig | None) -> DQConfigsContext:
    """Extract DQ report configs from YAML."""
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
    bronze_config = extract_single_dq_config(sink_mapping, "bronze", BronzeSinkConfig)
    silver_config = extract_single_dq_config(sink_mapping, "silver", SilverSinkConfig)
    gold_config = extract_single_dq_config(sink_mapping, "gold", GoldSinkConfig)

    return DQConfigsContext(
        bronze=bronze_config,
        silver=silver_config,
        gold=gold_config,
    )


def get_layer_path(
    config: object,
) -> str | None:
    """Extract path from layer config if available."""
    return getattr(config, "path", None) if config else None


def has_flat_structure(
    config: object,
) -> bool:
    """Check if layer config has flat_structure enabled."""
    return bool(config and getattr(config, "flat_structure", False))


def extract_dq_output_paths(
    yaml_config: PipelineYamlConfig | None,
) -> DQOutputPathsContext:
    """Extract DQ output paths and flat_structure from YAML config."""
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

    flat_structure = has_flat_structure(silver_config) or has_flat_structure(
        gold_config
    )

    return DQOutputPathsContext(
        bronze_path=get_layer_path(bronze_config),
        silver_path=get_layer_path(silver_config),
        gold_path=get_layer_path(gold_config),
        flat_structure=flat_structure,
    )
