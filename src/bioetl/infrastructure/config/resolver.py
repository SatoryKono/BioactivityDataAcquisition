"""Обёртка над загрузчиком конфигураций для обратной совместимости."""
from __future__ import annotations

from bioetl.domain.config_loader import load_pipeline_config_from_path
from bioetl.infrastructure.config.models import PipelineConfig


class ConfigResolver:
    """Загружает и валидирует конфиг пайплайна через config_loader."""

    def __init__(self, profiles_dir: str | None = None) -> None:
        self.profiles_dir = profiles_dir

    def resolve(self, config_path: str, profile: str = "default") -> PipelineConfig:
        profile_name = None if profile == "default" else profile
        return load_pipeline_config_from_path(config_path, profile=profile_name)


__all__ = ["ConfigResolver"]
