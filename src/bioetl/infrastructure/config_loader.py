"""Configuration loading utilities.

Handles loading and merging of YAML configuration files.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.source_config import SourceYamlConfig


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def _load_defaults(config_path: Path) -> dict[str, Any]:
    """Load pipeline defaults from _defaults.yaml."""
    defaults_path = config_path.parent.parent / "_defaults.yaml"

    if not defaults_path.exists():
        defaults_path = config_path.parent / "_defaults.yaml"

    if defaults_path.exists():
        with open(defaults_path, encoding="utf-8") as f:
            defaults = yaml.safe_load(f) or {}
            defaults.pop("defaults_version", None)
            return defaults

    return {}


@lru_cache(maxsize=10)
def load_source_config(provider: str) -> SourceYamlConfig:
    """Load source configuration from YAML file."""
    config_path = Path(f"configs/sources/{provider}.yaml")

    if not config_path.exists():
        raise ValueError(
            f"Source configuration file not found: {config_path}. "
            f"Create configs/sources/{provider}.yaml with rate_limit and circuit_breaker settings."
        )

    with open(config_path, encoding="utf-8") as f:
        raw_config = yaml.safe_load(f) or {}

    config: SourceYamlConfig = SourceYamlConfig.model_validate(raw_config)
    return config


@lru_cache(maxsize=10)
def load_pipeline_config(pipeline_name: str) -> PipelineYamlConfig:
    """Load pipeline configuration from YAML file and return typed model."""
    try:
        provider, entity = pipeline_name.split("_", 1)
        config_path = Path(f"configs/pipelines/{provider}/{entity}.yaml")
    except ValueError:
        config_path = Path(f"configs/pipelines/{pipeline_name}.yaml")

    if not config_path.exists():
        raise ValueError(f"Configuration file not found: {config_path}")

    defaults = _load_defaults(config_path)

    with open(config_path, encoding="utf-8") as f:
        entity_config = yaml.safe_load(f) or {}

    config = _deep_merge(defaults, entity_config)

    if source_file := config.get("source_file"):
        source_path = config_path.parent / source_file
        if source_path.exists():
            with open(source_path, encoding="utf-8") as f:
                source_config = yaml.safe_load(f) or {}
            config["source"] = source_config.get("source", source_config)

    validated: PipelineYamlConfig = PipelineYamlConfig.model_validate(config)
    return validated
