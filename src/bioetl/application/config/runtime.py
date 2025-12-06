"""Прикладной фасад для загрузки конфигураций пайплайнов."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioetl.domain.configs import PipelineConfig
from bioetl.infrastructure.config.loader import (
    load_pipeline_config,
    load_pipeline_config_from_path,
)


def build_runtime_config(
    *,
    pipeline_id: str | None = None,
    profile: str | None = None,
    config_path: str | Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
    env_overrides: dict[str, Any] | None = None,
    configs_root: str | Path | None = None,
) -> PipelineConfig:
    """
    Загружает конфигурацию пайплайна через инфраструктурный слой.

    Приоритет значений: CLI overrides → ENV overrides → YAML.
    """

    if config_path is not None:
        return load_pipeline_config_from_path(
            config_path,
            profile=profile,
            profiles_root=Path(configs_root) / "profiles"
            if configs_root
            else None,
            cli_overrides=cli_overrides,
            env_overrides=env_overrides,
        )

    if pipeline_id is None:
        raise ValueError("pipeline_id or config_path must be provided")

    return load_pipeline_config(
        pipeline_id,
        profile=profile,
        cli_overrides=cli_overrides,
        env_overrides=env_overrides,
        base_dir=configs_root,
    )


__all__ = ["build_runtime_config"]

