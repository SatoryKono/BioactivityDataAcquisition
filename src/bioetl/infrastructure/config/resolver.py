"""Обёртка над загрузчиком конфигураций для обратной совместимости."""
from __future__ import annotations

import os
from pathlib import Path

from bioetl.domain.config_loader import load_pipeline_config_from_path
from bioetl.infrastructure.config.models import PipelineConfig


class ConfigResolver:
    """Загружает и валидирует конфиг пайплайна через config_loader."""

    def __init__(
        self, profiles_dir: str | Path | None = None, base_dir: str | Path | None = None
    ) -> None:
        """
        Инициализирует resolver конфигураций.

        Args:
            profiles_dir: Путь к директории профилей (для обратной совместимости).
            base_dir: Базовая директория конфигов. Если не указана, используется
                     BIOETL_CONFIG_DIR или "configs" по умолчанию.
        """
        base_dir_value = base_dir or os.environ.get("BIOETL_CONFIG_DIR", "configs")
        self.base_dir = Path(base_dir_value)
        self.profiles_dir = Path(profiles_dir) if profiles_dir is not None else None

    def resolve(self, config_path: str, profile: str = "default") -> PipelineConfig:
        """
        Загружает и валидирует конфигурацию пайплайна.

        Args:
            config_path: Путь к файлу конфигурации (может быть относительным).
            profile: Имя профиля для применения (по умолчанию "default").

        Returns:
            Валидированная конфигурация пайплайна.
        """
        # Разрешаем путь относительно base_dir, если путь относительный и файл не существует
        config_path_obj = Path(config_path)
        if not config_path_obj.is_absolute() and not config_path_obj.exists():
            config_path_obj = self.base_dir / config_path_obj

        profile_name = None if profile == "default" else profile
        return load_pipeline_config_from_path(config_path_obj, profile=profile_name)


__all__ = ["ConfigResolver"]
