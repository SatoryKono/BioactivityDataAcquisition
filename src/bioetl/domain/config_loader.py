"""Загрузчик конфигураций пайплайнов со строгой валидацией."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from bioetl.domain.transform.merge import deep_merge
from bioetl.schemas.pipeline_config_schema import PipelineConfig
from bioetl.schemas.provider_config_schema import ProviderConfigUnion

CONFIGS_ROOT = Path("configs")
PIPELINES_ROOT = CONFIGS_ROOT / "pipelines"
PROFILES_ROOT = CONFIGS_ROOT / "profiles"


class ConfigError(Exception):
    """Базовая ошибка конфигурации."""


class ConfigFileNotFoundError(ConfigError):
    """Файл конфигурации не найден."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"Config file not found: {path}")
        self.path = path


class ConfigValidationError(ConfigError):
    """Ошибка валидации конфигурации."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path


class UnknownProviderError(ConfigError):
    """Указан неизвестный провайдер."""

    def __init__(self, provider: str) -> None:
        super().__init__(f"Unknown provider: {provider}")
        self.provider = provider


SUPPORTED_PROVIDERS = {"chembl"}


def load_pipeline_config(pipeline_id: str, profile: str | None = None) -> PipelineConfig:
    """Загружает конфиг по идентификатору вида "provider.entity"."""

    try:
        provider, entity = pipeline_id.split(".", maxsplit=1)
    except ValueError as exc:
        raise ConfigError(
            "Pipeline id must be in format '<provider>.<entity>'"
        ) from exc

    config_path = PIPELINES_ROOT / provider / f"{entity}.yaml"
    return load_pipeline_config_from_path(config_path, profile=profile)


def load_pipeline_config_from_path(
    config_path: str | Path, profile: str | None = None
) -> PipelineConfig:
    """Загружает и валидирует конфигурацию из файла."""

    path = Path(config_path)
    if not path.exists():
        raise ConfigFileNotFoundError(path)

    raw_config = _load_yaml(path)
    extends_profile = raw_config.pop("extends", None)

    merged_config: dict[str, Any] = {}
    if extends_profile:
        base_profile = _resolve_profile(extends_profile)
        merged_config = deep_merge(merged_config, base_profile)

    merged_config = deep_merge(merged_config, raw_config)

    if profile and profile != "default":
        profile_overrides = _resolve_profile(profile)
        merged_config = deep_merge(merged_config, profile_overrides)

    _validate_provider(merged_config, path)

    try:
        return PipelineConfig.model_validate(merged_config)
    except ValidationError as exc:
        raise ConfigValidationError(path, exc.__str__()) from exc


def _validate_provider(config: dict[str, Any], path: Path) -> None:
    provider = config.get("provider")
    if provider is None:
        raise ConfigValidationError(path, "'provider' field is required")
    if provider not in SUPPORTED_PROVIDERS:
        raise UnknownProviderError(str(provider))


_def_profile_cache: dict[str, dict[str, Any]] = {}


def _resolve_profile(profile_name: str) -> dict[str, Any]:
    if profile_name in _def_profile_cache:
        return _def_profile_cache[profile_name]

    profile_path = PROFILES_ROOT / f"{profile_name}.yaml"
    if not profile_path.exists():
        raise ConfigFileNotFoundError(profile_path)

    profile_data = _load_yaml(profile_path)
    parent = profile_data.get("extends")
    if parent:
        parent_data = _resolve_profile(parent)
        profile_data = deep_merge(parent_data, profile_data)

    _def_profile_cache[profile_name] = profile_data
    return profile_data


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ConfigValidationError(path, "YAML root must be a mapping")
    return data


__all__ = [
    "ConfigError",
    "ConfigFileNotFoundError",
    "ConfigValidationError",
    "UnknownProviderError",
    "load_pipeline_config",
    "load_pipeline_config_from_path",
]
