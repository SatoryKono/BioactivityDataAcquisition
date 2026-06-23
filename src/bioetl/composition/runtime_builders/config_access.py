"""Composition-facing seam for runtime configuration access helpers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

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


def create_pipeline_config_loader(
    configs_root: Path,
) -> Callable[[str], PipelineYamlConfig]:
    """Bind pipeline config loading to one explicit config root."""
    from bioetl.infrastructure.config.pipeline_config_api import (
        load_pipeline_config_from_root,
    )

    resolved_configs_root = resolve_configs_root(configs_root)

    def _load(pipeline_name: str) -> PipelineYamlConfig:
        return load_pipeline_config_from_root(
            pipeline_name,
            configs_root=resolved_configs_root,
        )

    return _load


def create_dq_config_loader(
    configs_root: Path,
) -> Callable[[str], object]:
    """Bind DQ config loading to one explicit config root."""
    from bioetl.infrastructure.config.dq_contract_config_loader import (
        load_dq_config_for_pipeline as _load_dq_config_for_pipeline,
    )

    resolved_configs_root = resolve_configs_root(configs_root)

    def _load(pipeline_name: str) -> object:
        return _load_dq_config_for_pipeline(
            pipeline_name,
            configs_root=resolved_configs_root,
        )

    return _load


def create_source_config_loader(
    configs_root: Path,
) -> Callable[[str], object]:
    """Bind provider source config loading to one explicit config root."""
    from bioetl.infrastructure.config.source_config_loader import (
        load_source_config_from_root,
    )

    resolved_configs_root = resolve_configs_root(configs_root)

    def _load(provider: str) -> object:
        return load_source_config_from_root(
            provider,
            configs_root=resolved_configs_root,
        )

    return _load
