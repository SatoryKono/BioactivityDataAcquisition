"""Загрузчик конфигураций пайплайнов (инфраструктура)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from bioetl.domain.configs import ClientConfig, PipelineConfig
from bioetl.domain.schemas import register_schemas
from bioetl.domain.schemas.fields import build_field_configs_from_schema
from bioetl.domain.schemas.pipeline_contracts import get_pipeline_contract
from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.transform.merge import apply_deep_merge
from bioetl.infrastructure.config.defaults_loader import get_defaults_config
from bioetl.infrastructure.config.env import resolve_env_placeholders
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
    get_yaml_from_path,
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


def get_pipeline_config(
    pipeline_id: str,
    *,
    profile: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
    env_overrides: dict[str, Any] | None = None,
    base_dir: str | Path | None = None,
) -> PipelineConfig:
    """Возвращает конфиг по идентификатору вида '<provider>.<entity>'."""

    config_path = resolve_pipeline_config_path(pipeline_id, base_dir=base_dir)
    try:
        config_path, merged_config = get_yaml_from_path(
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


def get_pipeline_config_from_path(
    config_path: str | Path,
    *,
    profile: str | None = None,
    profiles_root: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
    env_overrides: dict[str, Any] | None = None,
) -> PipelineConfig:
    """Возвращает и валидирует конфигурацию из файла."""

    try:
        path, merged_config = get_yaml_from_path(
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
    defaults = get_defaults_config(
        base_dir=config_path.parents[2] if len(config_path.parents) >= 3 else None
    )
    _validate_provider(merged_config, config_path, registry_path=registry_path)

    merged_config = _transform_legacy_config(
        merged_config, config_path, defaults=defaults
    )
    merged_config = _apply_overrides(
        merged_config,
        env_overrides=env_overrides,
        cli_overrides=cli_overrides,
    )
    merged_config = resolve_env_placeholders(merged_config)
    merged_config = _apply_defaults(merged_config, defaults)
    merged_config = _populate_fields_from_schema(merged_config)
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
        merged = apply_deep_merge(merged, env_overrides)
    if cli_overrides:
        merged = apply_deep_merge(merged, cli_overrides)
    return merged


def _apply_defaults(config: dict[str, Any], defaults: Any) -> dict[str, Any]:
    merged = dict(config)
    quality_section = merged.get("quality")
    if not isinstance(quality_section, dict):
        quality_section = {}
    quality_section.setdefault("hashing", defaults.hashing.hashing.model_dump())
    quality_section.setdefault(
        "normalization", defaults.normalization.normalization.model_dump()
    )
    merged["quality"] = quality_section
    return merged


def _populate_fields_from_schema(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("fields"):
        return config

    provider = config.get("provider")
    entity = config.get("entity")
    if not provider or not entity:
        return config

    contract = get_pipeline_contract(f"{provider}.{entity}", default_entity=str(entity))
    schema_name = contract.get_output_schema()

    registry = SchemaRegistry()
    register_schemas(registry)
    try:
        schema = registry.get_schema(schema_name)
    except ValueError:
        return config

    config = dict(config)
    config["fields"] = build_field_configs_from_schema(schema)
    return config


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


def _transform_legacy_config(
    config: dict[str, Any], path: Path, *, defaults: Any
) -> dict[str, Any]:
    """Преобразует старый формат конфигурации в новый."""
    transformed = config.copy()
    provider = transformed.get("provider", "chembl")

    _ensure_entity_fields(transformed, provider)
    _ensure_id(transformed, provider)
    _hydrate_provider_config(transformed, provider, defaults=defaults)
    _ensure_batch_size(transformed, defaults=defaults)
    _ensure_output_settings(transformed)
    _ensure_input_settings(transformed)
    _fold_quality_sections(transformed)
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


def _hydrate_provider_config(
    transformed: dict[str, Any], provider: str, *, defaults: Any
) -> None:
    if "sources" in transformed and "provider_config" not in transformed:
        transformed["provider_config"] = _build_provider_config_from_sources(
            transformed.pop("sources", {}),
            transformed,
            provider,
            defaults=defaults,
        )

    if "provider_config" not in transformed:
        transformed["provider_config"] = _default_provider_config(
            provider, defaults=defaults
        )

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
    *,
    defaults: Any,
) -> dict[str, Any]:
    chembl_source = sources.get("chembl", {})
    api_base_url = chembl_source.get("base_url") or transformed.pop(
        "api_base_url", None
    )
    if not api_base_url:
        api_base_url = _resolve_base_url(provider, defaults=defaults)

    runtime_client = transformed.get("client", {})
    source_client = chembl_source.get("client", {})
    provider_config: dict[str, Any] = {
        "provider": provider,
        "base_url": api_base_url,
        "client": _compose_client_config(runtime_client, source_client, defaults=defaults),
    }

    provider_defaults = getattr(defaults, "get_source_default", lambda *_: None)(
        provider
    )

    if provider_defaults is not None:
        provider_config = apply_deep_merge(
            provider_config,
            provider_defaults.model_dump(exclude_none=True),
        )

    for optional_key in ("max_url_length", "batch_size"):
        if optional_key in chembl_source:
            provider_config[optional_key] = chembl_source[optional_key]
    return provider_config


def _default_provider_config(provider: str, *, defaults: Any) -> dict[str, Any]:
    provider_config = {
        "provider": provider,
        "base_url": _resolve_base_url(provider, defaults=defaults),
        "client": _compose_client_config({}, {}, defaults=defaults),
    }

    provider_defaults = getattr(defaults, "get_source_default", lambda *_: None)(
        provider
    )
    if provider_defaults is not None:
        provider_config = apply_deep_merge(
            provider_config,
            provider_defaults.model_dump(exclude_none=True),
        )

    if (
        provider_config.get("max_url_length") is None
        and getattr(defaults, "network", None) is not None
    ):
        http_defaults = getattr(defaults.network, "http", None)
        if http_defaults and http_defaults.default.max_url_length is not None:
            provider_config["max_url_length"] = http_defaults.default.max_url_length

    return provider_config


def _compose_client_config(
    runtime_client: dict[str, Any],
    source_client: dict[str, Any],
    *,
    defaults: Any,
) -> dict[str, Any]:
    client_config = _resolve_http_client_defaults(defaults)
    if runtime_client:
        client_config = apply_deep_merge(client_config, runtime_client)
    if source_client:
        client_config = apply_deep_merge(client_config, source_client)
    return client_config


def _resolve_http_client_defaults(defaults: Any) -> dict[str, Any]:
    network_defaults = getattr(defaults, "network", None)
    http_defaults = getattr(network_defaults, "http", None) if network_defaults else None
    client_defaults = getattr(http_defaults, "client", None) if http_defaults else None
    if client_defaults is not None:
        return client_defaults.model_dump()
    return ClientConfig().model_dump()


def _resolve_base_url(provider: str, *, defaults: Any) -> str:
    provider_defaults = getattr(defaults, "get_source_default", lambda *_: None)(
        provider
    )
    if provider_defaults and provider_defaults.base_url:
        return str(provider_defaults.base_url)
    # Fallback to known Chembl URL for backwards compatibility
    return "https://www.ebi.ac.uk/chembl/api/data"


def _ensure_batch_size(transformed: dict[str, Any], *, defaults: Any) -> None:
    if "batch_size" in transformed:
        return

    provider_defaults = getattr(defaults, "get_source_default", lambda *_: None)(
        transformed.get("provider", "")
    )
    if provider_defaults and provider_defaults.batch_size is not None:
        transformed["batch_size"] = provider_defaults.batch_size
        return

    transformed["batch_size"] = 20


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


def _fold_quality_sections(transformed: dict[str, Any]) -> None:
    quality_section = transformed.get("quality")
    if not isinstance(quality_section, dict):
        quality_section = {}

    for key in ("determinism", "hashing", "normalization"):
        if key not in transformed:
            continue
        value = transformed.pop(key)
        if isinstance(value, dict) and isinstance(quality_section.get(key), dict):
            quality_section[key] = apply_deep_merge(quality_section[key], value)
        else:
            quality_section[key] = value

    if quality_section:
        transformed["quality"] = quality_section


def _drop_legacy_fields(transformed: dict[str, Any]) -> None:
    for field in (
        "endpoint",
        "api_base_url",
        "sources",
        "determinism",
        "hashing",
        "normalization",
    ):
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
    "get_pipeline_config",
    "get_pipeline_config_from_path",
]
