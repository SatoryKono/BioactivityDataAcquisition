"""Загрузчик конфигураций пайплайнов."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from bioetl.domain.configs import ConfigMigrator, PipelineConfig
from bioetl.domain.errors import ConfigError, ConfigValidationError
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.transform.merge import apply_deep_merge
from bioetl.infrastructure.config.env import resolve_env_placeholders
from bioetl.infrastructure.config.provider_registry import (
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

    # Migration is handled by PipelineConfig.migrate_legacy_format validator,
    # which delegates to ConfigMigrator. We also apply it here to ensure
    # provider_config is extracted from sources before provider validation.
    merged = ConfigMigrator.migrate(merged)

    # After migration, provider is in identity section
    identity = merged.get("identity", {})
    provider_id = identity.get("provider") if isinstance(identity, dict) else None
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


_SCHEMA_CONTRACT_PROVIDER: SchemaContractProviderABC | None = None


def set_schema_contract_provider(provider: SchemaContractProviderABC) -> None:
    """Set the global schema contract provider.

    This function allows the application layer to inject a configured
    schema contract provider into the infrastructure layer. This is
    typically called during container bootstrap.

    Args:
        provider: Configured SchemaContractProviderABC instance.

    Example:
        >>> from bioetl.application.services import SchemaContractProviderImpl
        >>> from bioetl.domain.schemas.registry import get_default_schema_registry
        >>> provider = SchemaContractProviderImpl(get_default_schema_registry())
        >>> set_schema_contract_provider(provider)
    """
    global _SCHEMA_CONTRACT_PROVIDER  # noqa: PLW0603
    _SCHEMA_CONTRACT_PROVIDER = provider


def get_schema_contract_provider() -> SchemaContractProviderABC | None:
    """Get the current schema contract provider.

    Returns:
        The configured schema contract provider, or None if not set.
    """
    return _SCHEMA_CONTRACT_PROVIDER


def clear_schema_contract_provider() -> None:
    """Clear the global schema contract provider (for testing).

    This resets the provider to None, useful for test isolation.
    """
    global _SCHEMA_CONTRACT_PROVIDER  # noqa: PLW0603
    _SCHEMA_CONTRACT_PROVIDER = None


def reset_schema_contract_provider() -> None:
    """Reset the schema contract provider (for testing purposes).

    Deprecated: Use clear_schema_contract_provider() instead.
    This function is kept for backward compatibility.
    """
    clear_schema_contract_provider()


def _populate_fields_from_schema(config: PipelineConfig) -> None:
    """Populate config.fields using injected schema contract provider."""
    if config.fields:
        return

    if _SCHEMA_CONTRACT_PROVIDER is None:
        raise RuntimeError(
            "SchemaContractProvider not initialized. "
            "Call application bootstrap before loading configs."
        )

    schema_name = _SCHEMA_CONTRACT_PROVIDER.get_output_schema_name(
        config.id,
        default_entity=config.entity_name,
    )

    try:
        fields = _SCHEMA_CONTRACT_PROVIDER.get_field_configs(schema_name)
    except ValueError as exc:
        raise ConfigValidationError(
            f"Schema '{schema_name}' is not registered for pipeline '{config.id}'"
        ) from exc
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

    if config.source.input_mode not in {"csv", "id_only"}:
        return

    input_path = config.source.input_path
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


__all__ = [
    "ConfigFileNotFoundError",
    "UnknownProviderError",
    "get_pipeline_config",
    "get_pipeline_config_from_path",
    "set_schema_contract_provider",
    "get_schema_contract_provider",
    "clear_schema_contract_provider",
    "reset_schema_contract_provider",
]
