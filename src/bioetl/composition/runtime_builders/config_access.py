"""Composition-facing seam for runtime configuration access helpers."""

from __future__ import annotations

from pathlib import Path

from bioetl.composition.runtime_builders._config_access_loaders import (
    create_dq_config_loader,
    create_pipeline_config_loader,
    create_source_config_loader,
)
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "create_dq_config_loader",
    "create_pipeline_config_loader",
    "create_source_config_loader",
    "get_settings",
    "load_dq_config_for_pipeline",
    "load_pipeline_config",
    "load_source_config",
    "resolve_configs_root",
]


def get_settings():
    """Resolve settings through the infrastructure package at call time."""
    from bioetl.infrastructure.config.settings_api import get_settings as _get_settings

    return _get_settings()


def load_pipeline_config(pipeline_name: str) -> PipelineYamlConfig:
    """Load pipeline YAML through the canonical infrastructure entrypoint."""
    from bioetl.infrastructure.config.pipeline_config_api import (
        load_pipeline_config as _load_pipeline_config,
    )

    return _load_pipeline_config(pipeline_name)


def load_source_config(provider: str) -> object:
    """Load source YAML through the canonical infrastructure entrypoint."""
    from bioetl.infrastructure.config.source_config_loader import (
        load_source_config as _load_source_config,
    )

    return _load_source_config(provider)


def load_dq_config_for_pipeline(
    pipeline_name: str,
    *,
    configs_root: Path | None = None,
) -> object:
    """Load DQ config through the canonical infrastructure entrypoint."""
    from bioetl.infrastructure.config.dq_contract_config_loader import (
        load_dq_config_for_pipeline as _load_dq_config_for_pipeline,
    )

    if configs_root is None:
        configs_root = resolve_configs_root(None)
    return _load_dq_config_for_pipeline(pipeline_name, configs_root=configs_root)
