"""Загрузчик конфигураций пайплайнов (инфраструктура)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from bioetl.domain.configs import PipelineConfig
from bioetl.domain.transform.merge import deep_merge
from bioetl.infrastructure.config.provider_registry_loader import (
    DEFAULT_PROVIDERS_REGISTRY_PATH,
    ProviderNotConfiguredError,
    ProviderRegistryError,
    ProviderRegistryFormatError,
    ProviderRegistryNotFoundError,
    ensure_provider_known,
)
from bioetl.infrastructure.config.sources import (
    get_configs_root,
    read_yaml_from_path,
    resolve_pipeline_config_path,
)


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

    def __init__(self, provider: str, *, registry_path: Path | None = None) -> None:
        suffix = f" in registry {registry_path}" if registry_path else ""
        super().__init__(f"Unknown provider: {provider}{suffix}")
        self.provider = provider
        self.registry_path = registry_path


def load_pipeline_config(
    pipeline_id: str,
    *,
    profile: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
    env_overrides: dict[str, Any] | None = None,
    base_dir: str | Path | None = None,
) -> PipelineConfig:
    """Загружает конфиг по идентификатору вида '<provider>.<entity>'."""

    config_path = resolve_pipeline_config_path(pipeline_id, base_dir=base_dir)
    try:
        config_path, merged_config = read_yaml_from_path(
            config_path,
            profile=profile,
            profiles_root=get_configs_root(base_dir) / "profiles",
        )
    except FileNotFoundError as exc:
        raise ConfigFileNotFoundError(config_path) from exc

    registry_path = _resolve_registry_path(
        get_configs_root(base_dir) / "providers.yaml"
    )
    return _finalize_config(
        merged_config,
        config_path,
        cli_overrides=cli_overrides,
        env_overrides=env_overrides,
        registry_path=registry_path,
    )


def load_pipeline_config_from_path(
    config_path: str | Path,
    *,
    profile: str | None = None,
    profiles_root: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
    env_overrides: dict[str, Any] | None = None,
) -> PipelineConfig:
    """Загружает и валидирует конфигурацию из файла."""

    try:
        path, merged_config = read_yaml_from_path(
            config_path,
            profile=profile,
            profiles_root=profiles_root,
        )
    except FileNotFoundError as exc:
        raise ConfigFileNotFoundError(Path(config_path)) from exc

    configs_root = path.parents[2] if len(path.parents) >= 3 else path.parent
    registry_path = _resolve_registry_path(configs_root / "providers.yaml")
    return _finalize_config(
        merged_config,
        path,
        cli_overrides=cli_overrides,
        env_overrides=env_overrides,
        registry_path=registry_path,
    )


def _resolve_registry_path(candidate: Path) -> Path:
    """
    Возвращает путь к реестру провайдеров, падая обратно на дефолтный,
    если локальный файл отсутствует.
    """

    if candidate.exists():
        return candidate
    return DEFAULT_PROVIDERS_REGISTRY_PATH


def _finalize_config(
    merged_config: dict[str, Any],
    config_path: Path,
    *,
    cli_overrides: dict[str, Any] | None,
    env_overrides: dict[str, Any] | None,
    registry_path: Path,
) -> PipelineConfig:
    _validate_provider(merged_config, config_path, registry_path=registry_path)

    merged_config = _transform_legacy_config(merged_config, config_path)
    merged_config = _apply_overrides(
        merged_config,
        env_overrides=env_overrides,
        cli_overrides=cli_overrides,
    )
    _validate_input_path_exists(merged_config, config_path)

    try:
        return PipelineConfig.model_validate(merged_config)
    except ValidationError as exc:
        raise ConfigValidationError(config_path, exc.__str__()) from exc


def _apply_overrides(
    base_config: dict[str, Any],
    *,
    env_overrides: dict[str, Any] | None,
    cli_overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(base_config)
    if env_overrides:
        merged = deep_merge(merged, env_overrides)
    if cli_overrides:
        merged = deep_merge(merged, cli_overrides)
    return merged


def _validate_provider(
    config: dict[str, Any],
    path: Path,
    *,
    registry_path: Path,
) -> None:
    provider = config.get("provider")
    if provider is None:
        raise ConfigValidationError(path, "'provider' field is required")

    try:
        ensure_provider_known(str(provider), registry_path=registry_path)
    except ProviderNotConfiguredError as exc:
        raise UnknownProviderError(
            str(provider),
            registry_path=exc.registry_path,
        ) from exc
    except ProviderRegistryNotFoundError as exc:
        # Отсутствие реестра трактуем как неизвестного провайдера
        raise UnknownProviderError(
            str(provider),
            registry_path=exc.registry_path,
        ) from exc
    except ProviderRegistryFormatError as exc:
        raise ConfigValidationError(path, str(exc)) from exc
    except ProviderRegistryError as exc:  # pragma: no cover - defensive
        raise ConfigValidationError(path, str(exc)) from exc


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


def _validate_input_path_exists(config: dict[str, Any], config_path: Path) -> None:
    input_path = config.get("input_path")
    if input_path is None or input_path == "":
        return

    input_path_obj = Path(str(input_path))
    if not input_path_obj.exists():
        raise ConfigValidationError(
            config_path, f"Input path does not exist: {input_path}"
        )

    config["input_path"] = str(input_path_obj)


__all__ = [
    "ConfigError",
    "ConfigFileNotFoundError",
    "ConfigValidationError",
    "UnknownProviderError",
    "load_pipeline_config",
    "load_pipeline_config_from_path",
]
