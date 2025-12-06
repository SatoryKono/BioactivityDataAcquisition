"""Загрузчик конфигураций пайплайнов со строгой валидацией."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from bioetl.config.pipeline_config_schema import PipelineConfig
from bioetl.domain.transform.merge import deep_merge

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


def load_pipeline_config(
    pipeline_id: str, profile: str | None = None
) -> PipelineConfig:
    """Загружает конфиг по идентификатору вида \"provider.entity\"."""

    try:
        provider, entity = pipeline_id.split(".", maxsplit=1)
    except ValueError as exc:
        raise ConfigError(
            "Pipeline id must be in format '<provider>.<entity>'"
        ) from exc

    config_path = PIPELINES_ROOT / provider / f"{entity}.yaml"
    return load_pipeline_config_from_path(config_path, profile=profile)


def load_pipeline_config_from_path(
    config_path: str | Path,
    profile: str | None = None,
    profiles_root: Path | None = None,
) -> PipelineConfig:
    """Загружает и валидирует конфигурацию из файла."""

    path = Path(config_path)
    if not path.exists():
        raise ConfigFileNotFoundError(path)

    raw_config = _load_yaml(path)
    extends_profile = raw_config.pop("extends", None)

    merged_config: dict[str, Any] = {}
    if extends_profile:
        base_profile = _resolve_profile(extends_profile, profiles_root=profiles_root)
        merged_config = deep_merge(merged_config, base_profile)

    merged_config = deep_merge(merged_config, raw_config)
    merged_config.pop("extends", None)

    if profile and profile != "default":
        profile_overrides = _resolve_profile(profile, profiles_root=profiles_root)
        merged_config = deep_merge(merged_config, profile_overrides)

    _validate_provider(merged_config, path)

    merged_config = _transform_legacy_config(merged_config, path)

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


def _transform_legacy_config(config: dict[str, Any], path: Path) -> dict[str, Any]:
    """Преобразует старый формат конфигурации в новый."""
    transformed = config.copy()
    provider = transformed.get("provider", "chembl")

    _ensure_entity_fields(transformed, provider)
    _ensure_id(transformed, provider)
    _hydrate_provider_config(transformed, provider)
    _ensure_batch_size(transformed)
    _ensure_output_settings(transformed)
    _ensure_input_settings(transformed)
    _drop_legacy_fields(transformed)

    return transformed


def _ensure_entity_fields(transformed: dict[str, Any], provider: str) -> None:
    if "entity_name" in transformed and "entity" not in transformed:
        transformed["entity"] = transformed.pop("entity_name")
    transformed.setdefault("provider", provider)


def _ensure_id(transformed: dict[str, Any], provider: str) -> None:
    if "id" in transformed:
        return
    entity = transformed.get("entity", transformed.get("entity_name", "unknown"))
    transformed["id"] = f"{provider}.{entity}"


def _hydrate_provider_config(transformed: dict[str, Any], provider: str) -> None:
    if "sources" in transformed and "provider_config" not in transformed:
        transformed["provider_config"] = _build_provider_config_from_sources(
            transformed.pop("sources", {}),
            transformed,
            provider,
        )

    if "provider_config" not in transformed:
        transformed["provider_config"] = _default_provider_config(provider)

    provider_cfg = transformed.get("provider_config")
    if (
        isinstance(provider_cfg, dict)
        and "batch_size" in provider_cfg
        and "batch_size" not in transformed
    ):
        transformed["batch_size"] = provider_cfg["batch_size"]


def _build_provider_config_from_sources(
    sources: dict[str, Any],
    transformed: dict[str, Any],
    provider: str,
) -> dict[str, Any]:
    chembl_source = sources.get("chembl", {})
    api_base_url = chembl_source.get("base_url") or transformed.pop(
        "api_base_url", None
    )
    if not api_base_url:
        api_base_url = "https://www.ebi.ac.uk/chembl/api/data"

    provider_config: dict[str, Any] = {
        "provider": provider,
        "base_url": api_base_url,
        "timeout_sec": transformed.get("client", {}).get("timeout", 30.0),
        "max_retries": transformed.get("client", {}).get("max_retries", 3),
        "rate_limit_per_sec": transformed.get("client", {}).get("rate_limit", 10.0),
    }

    for optional_key in ("max_url_length", "batch_size"):
        if optional_key in chembl_source:
            provider_config[optional_key] = chembl_source[optional_key]
    return provider_config


def _default_provider_config(provider: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "base_url": "https://www.ebi.ac.uk/chembl/api/data",
        "timeout_sec": 30.0,
        "max_retries": 3,
        "rate_limit_per_sec": 10.0,
    }


def _ensure_batch_size(transformed: dict[str, Any]) -> None:
    transformed.setdefault("batch_size", 20)


def _ensure_output_settings(transformed: dict[str, Any]) -> None:
    if "output_path" in transformed:
        return

    storage = transformed.get("storage", {})
    if isinstance(storage, dict) and "output_path" in storage:
        transformed["output_path"] = storage["output_path"]
        return

    entity = transformed.get("entity", "unknown")
    transformed["output_path"] = f"./data/output/{entity}"


def _ensure_input_settings(transformed: dict[str, Any]) -> None:
    transformed.setdefault("input_mode", "auto_detect")
    transformed.setdefault("input_path", None)


def _drop_legacy_fields(transformed: dict[str, Any]) -> None:
    for field in ("endpoint", "api_base_url", "sources"):
        transformed.pop(field, None)


_def_profile_cache: dict[str, dict[str, Any]] = {}


def _resolve_profile(
    profile_name: str, profiles_root: Path | None = None
) -> dict[str, Any]:
    profiles_dir = profiles_root or PROFILES_ROOT
    cache_key = f"{profiles_dir}:{profile_name}"

    if cache_key in _def_profile_cache:
        return _def_profile_cache[cache_key]

    profile_path = profiles_dir / f"{profile_name}.yaml"
    if not profile_path.exists():
        raise ConfigFileNotFoundError(profile_path)

    profile_data = _load_yaml(profile_path)
    parent = profile_data.get("extends")
    if parent:
        parent_data = _resolve_profile(parent, profiles_root=profiles_root)
        profile_data = deep_merge(parent_data, profile_data)

    _def_profile_cache[cache_key] = profile_data
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
