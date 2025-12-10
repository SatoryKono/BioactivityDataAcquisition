"""Загрузчик конфигураций пайплайнов."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from bioetl.domain.configs import PipelineConfig
from bioetl.domain.errors import ConfigError, ConfigValidationError
from bioetl.domain.schemas import register_schemas
from bioetl.domain.schemas.fields import build_field_configs_from_schema
from bioetl.domain.schemas.pipeline_contracts import get_pipeline_contract
from bioetl.domain.schemas.registry import default_schema_provider
from bioetl.domain.transform.merge import apply_deep_merge
from bioetl.domain.validation import SchemaProviderABC
from bioetl.infrastructure.config.env import resolve_env_placeholders
from bioetl.infrastructure.config.provider_registry_loader import (
    ProviderNotConfiguredError,
    ProviderRegistryError,
    ensure_provider_known,
)
from bioetl.infrastructure.config.sources import (
    get_yaml_for_pipeline,
    get_yaml_from_path,
)


class ConfigFileNotFoundError(ConfigError):
    """Файл конфигурации не найден."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"Config file not found: {path}")
        self.path = path


class UnknownProviderError(ConfigError):
    """Неизвестный провайдер."""

    def __init__(self, provider: str) -> None:
        super().__init__(f"Unknown provider: {provider}")
        self.provider = provider


def get_pipeline_config(
    pipeline_id: str,
    *,
    profile: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
    env_overrides: dict[str, Any] | None = None,
    base_dir: str | Path | None = None,
) -> PipelineConfig:
    """Загружает конфигурацию пайплайна по идентификатору."""

    try:
        config_path, raw_config = get_yaml_for_pipeline(
            pipeline_id,
            profile=profile,
            base_dir=base_dir,
        )
    except FileNotFoundError as exc:
        path_str = str(exc).rsplit(": ", maxsplit=1)[-1]
        raise ConfigFileNotFoundError(Path(path_str)) from exc

    return _build_config(
        raw_config,
        config_path=config_path,
        cli_overrides=cli_overrides,
        env_overrides=env_overrides,
        base_dir=Path(base_dir) if base_dir is not None else None,
    )


def get_pipeline_config_from_path(
    config_path: str | Path,
    *,
    profile: str | None = None,
    profiles_root: str | Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
    env_overrides: dict[str, Any] | None = None,
) -> PipelineConfig:
    """Загружает конфигурацию пайплайна из файла."""

    try:
        path, raw_config = get_yaml_from_path(
            config_path,
            profile=profile,
            profiles_root=profiles_root,
        )
    except FileNotFoundError as exc:
        path_str = str(exc).rsplit(": ", maxsplit=1)[-1]
        raise ConfigFileNotFoundError(Path(path_str)) from exc

    return _build_config(
        raw_config,
        config_path=path,
        cli_overrides=cli_overrides,
        env_overrides=env_overrides,
        base_dir=None,
    )


def _build_config(
    raw_config: dict[str, Any],
    *,
    config_path: Path,
    cli_overrides: dict[str, Any] | None = None,
    env_overrides: dict[str, Any] | None = None,
    base_dir: Path | None = None,
) -> PipelineConfig:
    """Собирает PipelineConfig из сырых данных с применением overrides."""

    merged = resolve_env_placeholders(dict(raw_config))

    # Применяем overrides в порядке приоритета: env → CLI
    if env_overrides:
        env_values = resolve_env_placeholders(env_overrides)
        merged = apply_deep_merge(merged, env_values)
    if cli_overrides:
        cli_values = resolve_env_placeholders(cli_overrides)
        merged = apply_deep_merge(merged, cli_values)
    _migrate_legacy_pipeline_config(merged)

    provider_id = merged.get("provider")
    if isinstance(provider_id, str):
        _ensure_provider_registered(provider_id)

    try:
        config = PipelineConfig.model_validate(merged)
    except ValidationError as exc:
        raise ConfigValidationError(
            f"Validation failed for {config_path}: {exc}"
        ) from exc
    _ensure_input_source_valid(config, config_path=config_path, base_dir=base_dir)
    _populate_fields_from_schema(config)
    return config


def _ensure_provider_registered(provider_id: str) -> None:
    """Проверяет наличие провайдера в реестре до валидации схемы."""

    try:
        ensure_provider_known(provider_id)
    except ProviderNotConfiguredError as exc:
        raise UnknownProviderError(provider_id) from exc
    except ProviderRegistryError as exc:
        raise ConfigError(
            f"Failed to verify provider '{provider_id}' against registry: {exc}"
        ) from exc


_SCHEMA_PROVIDER: SchemaProviderABC | None = None
_SCHEMAS_REGISTERED = False


def _get_schema_provider() -> SchemaProviderABC:
    """Возвращает провайдера схем, гарантируя регистрацию стандартных сущностей."""

    global _SCHEMA_PROVIDER, _SCHEMAS_REGISTERED  # noqa: PLW0603

    if _SCHEMA_PROVIDER is None:
        _SCHEMA_PROVIDER = default_schema_provider()
    if not _SCHEMAS_REGISTERED:
        register_schemas(_SCHEMA_PROVIDER)
        _SCHEMAS_REGISTERED = True
    return _SCHEMA_PROVIDER


def _populate_fields_from_schema(config: PipelineConfig) -> None:
    """Автоматически заполняет config.fields, если секция отсутствует в YAML."""

    if config.fields:
        return

    contract = get_pipeline_contract(config.id, default_entity=config.entity_name)
    schema_name = contract.get_output_schema()
    provider = _get_schema_provider()

    try:
        schema = provider.get_schema(schema_name)
    except ValueError as exc:
        raise ConfigValidationError(
            f"Schema '{schema_name}' is not registered for pipeline '{config.id}'"
        ) from exc

    try:
        fields = build_field_configs_from_schema(schema)
    except Exception as exc:  # pragma: no cover - защитный контур
        raise ConfigValidationError(
            f"Failed to derive fields from schema '{schema_name}' "
            f"for pipeline '{config.id}': {exc}"
        ) from exc

    if not fields:
        raise ConfigValidationError(
            f"Schema '{schema_name}' produced empty field list "
            f"for pipeline '{config.id}'"
        )

    config.fields = fields


def _ensure_input_source_valid(
    config: PipelineConfig,
    *,
    config_path: Path,
    base_dir: Path | None,
) -> None:
    """Проверяет доступность локальных файлов для CSV/id-only режимов."""

    if config.input_mode not in {"csv", "id_only"}:
        return

    input_path = config.input_path
    if not input_path:
        raise ConfigValidationError(
            "input_path must be provided when input_mode is 'csv' or 'id_only'"
        )

    resolved = _resolve_existing_input_path(
        input_path,
        config_path=config_path,
        base_dir=base_dir,
    )
    if resolved is None:
        raise ConfigValidationError(
            f"input_path '{input_path}' for pipeline '{config.id}' "
            "does not exist or is not accessible"
        )


def _resolve_existing_input_path(
    path_str: str,
    *,
    config_path: Path,
    base_dir: Path | None,
) -> Path | None:
    """Пытается разрешить относительный путь к существующему файлу."""

    candidate = Path(path_str).expanduser()
    if candidate.is_absolute():
        return candidate if candidate.exists() else None

    for root in _iter_candidate_roots(config_path=config_path, base_dir=base_dir):
        resolved = (root / candidate).resolve()
        if resolved.exists():
            return resolved
    return None


def _iter_candidate_roots(
    *,
    config_path: Path,
    base_dir: Path | None,
) -> Iterable[Path]:
    """Генерирует директории, относительно которых ищем входной файл."""

    bases: list[Path] = []
    if base_dir is not None:
        bases.append(base_dir.resolve())
    bases.append(Path.cwd().resolve())
    bases.append(config_path.parent.resolve())
    bases.extend(parent.resolve() for parent in config_path.parents)

    seen: set[Path] = set()
    for base in bases:
        if base in seen:
            continue
        seen.add(base)
        yield base


def _migrate_legacy_pipeline_config(config: dict[str, Any]) -> None:
    """Приводит устаревшие конфиги (entity_name, sources и т.д.) к актуальной схеме."""

    entity_alias = config.get("entity") or config.get("entity_name")
    if "entity" not in config and entity_alias:
        config["entity"] = entity_alias
    config.pop("entity_name", None)

    provider = config.get("provider")
    pipeline_section = config.get("pipeline")
    if "id" not in config:
        if isinstance(pipeline_section, dict) and pipeline_section.get("name"):
            config["id"] = pipeline_section["name"]
        elif provider and config.get("entity"):
            config["id"] = f"{provider}.{config['entity']}"

    if "output_path" not in config:
        storage_section = config.get("storage")
        if isinstance(storage_section, dict) and "output_path" in storage_section:
            config["output_path"] = storage_section["output_path"]

    if "batch_size" not in config:
        batch_size = _resolve_batch_size_from_sources(config)
        if batch_size is not None:
            config["batch_size"] = batch_size

    if "provider_config" not in config:
        provider_config = _extract_provider_config(config)
        if provider_config is not None:
            config["provider_config"] = provider_config

    config.pop("sources", None)

    def _pack(target_section: str, keys: list[str]) -> None:
        if target_section not in config:
            config[target_section] = {}
        target = config[target_section]
        if not isinstance(target, dict):
            return

        for key in keys:
            if key in config:
                target[key] = config.pop(key)

    _pack("runtime", ["pagination", "client", "storage", "csv", "csv_options"])
    _pack("observability", ["logging", "metrics"])
    _pack("quality", ["determinism", "qc", "hashing", "normalization"])
    _pack("features", ["features", "interface_features", "interfaces"])
    _pack("output", ["output"])

    # Fix legacy client config keys
    runtime = config.get("runtime")
    if isinstance(runtime, dict):
        client = runtime.get("client")
        if isinstance(client, dict):
            if "timeout" in client:
                client["timeout_sec"] = client.pop("timeout")
            if "rate_limit" in client:
                client["rate_limit_per_sec"] = client.pop("rate_limit")
            if "backoff" in client:
                client["backoff_factor"] = client.pop("backoff")

    # Fix legacy api_base_url
    if "api_base_url" in config:
        provider_conf = config.get("provider_config")
        if isinstance(provider_conf, dict):
            provider_conf["base_url"] = config.pop("api_base_url")
        else:
            config.pop("api_base_url")


def _resolve_batch_size_from_sources(config: dict[str, Any]) -> int | None:
    sources_section = config.get("sources")
    if not isinstance(sources_section, dict):
        return None

    provider = config.get("provider")
    source_entry: Any | None = None
    if provider and provider in sources_section:
        source_entry = sources_section[provider]
    elif len(sources_section) == 1:
        source_entry = next(iter(sources_section.values()))

    if isinstance(source_entry, dict):
        batch_size = source_entry.get("batch_size")
        if isinstance(batch_size, int):
            return batch_size
    return None


def _extract_provider_config(config: dict[str, Any]) -> dict[str, Any] | None:
    sources_section = config.get("sources")
    if not isinstance(sources_section, dict):
        return None

    provider = config.get("provider")
    source_entry: Any | None = None
    if provider and provider in sources_section:
        source_entry = sources_section[provider]
    elif len(sources_section) == 1:
        source_entry = next(iter(sources_section.values()))

    if not isinstance(source_entry, dict):
        return None

    provider_config = dict(source_entry)
    if "provider" not in provider_config and provider:
        provider_config["provider"] = provider
    return provider_config


__all__ = [
    "ConfigFileNotFoundError",
    "UnknownProviderError",
    "get_pipeline_config",
    "get_pipeline_config_from_path",
]
