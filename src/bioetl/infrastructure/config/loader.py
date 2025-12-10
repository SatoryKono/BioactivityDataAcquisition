"""Загрузчик конфигураций пайплайнов.

This module provides pipeline configuration loading functionality with support
for dependency injection of schema contract providers.

Preferred usage (DI approach):
    >>> from bioetl.interfaces.composition_root import get_composition_root
    >>> root = get_composition_root()
    >>> loader = root.create_schema_contract_loader()
    >>> config = loader.get_pipeline_config("chembl.activity")

Legacy usage (deprecated, will be removed):
    >>> from bioetl.infrastructure.config.loader import get_pipeline_config
    >>> set_schema_contract_provider(provider)  # deprecated
    >>> config = get_pipeline_config("chembl.activity")
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from bioetl.domain.configs import PipelineConfig
from bioetl.infrastructure.config.migration import ConfigMigrator
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


# ============================================================================
# SchemaContractLoader - DI-based configuration loader
# ============================================================================


class SchemaContractLoader:
    """Configuration loader with injected schema contract provider.

    This class provides the preferred DI-based approach for loading pipeline
    configurations. The schema contract provider is injected through the
    constructor, eliminating global state.

    Example:
        >>> from bioetl.interfaces.composition_root import get_composition_root
        >>> root = get_composition_root()
        >>> loader = root.create_schema_contract_loader()
        >>> config = loader.get_pipeline_config("chembl.activity")

    Attributes:
        schema_contract_provider: The injected schema contract provider.
    """

    def __init__(self, schema_contract_provider: SchemaContractProviderABC) -> None:
        """Initialize loader with schema contract provider.

        Args:
            schema_contract_provider: Provider for schema contracts.
                Must not be None.

        Raises:
            ValueError: If schema_contract_provider is None.
        """
        if schema_contract_provider is None:
            raise ValueError("schema_contract_provider must not be None")
        self._schema_contract_provider = schema_contract_provider

    @property
    def schema_contract_provider(self) -> SchemaContractProviderABC:
        """Get the schema contract provider."""
        return self._schema_contract_provider

    def get_pipeline_config(
        self,
        pipeline_id: str,
        *,
        profile: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
        env_overrides: dict[str, Any] | None = None,
        base_dir: str | Path | None = None,
    ) -> PipelineConfig:
        """Load pipeline configuration by identifier.

        Args:
            pipeline_id: Pipeline identifier (e.g., "chembl.activity").
            profile: Profile name to apply.
            cli_overrides: CLI overrides.
            env_overrides: Environment variable overrides.
            base_dir: Base directory for configuration search.

        Returns:
            Loaded and validated pipeline configuration.

        Raises:
            ConfigFileNotFoundError: Configuration file not found.
            ConfigValidationError: Configuration validation failed.
            UnknownProviderError: Unknown provider in configuration.
        """
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
            schema_contract_provider=self._schema_contract_provider,
            cli_overrides=cli_overrides,
            env_overrides=env_overrides,
            base_dir=Path(base_dir) if base_dir is not None else None,
        )

    def get_pipeline_config_from_path(
        self,
        config_path: str | Path,
        *,
        profile: str | None = None,
        profiles_root: str | Path | None = None,
        cli_overrides: dict[str, Any] | None = None,
        env_overrides: dict[str, Any] | None = None,
    ) -> PipelineConfig:
        """Load pipeline configuration from file path.

        Args:
            config_path: Path to configuration file.
            profile: Profile name to apply.
            profiles_root: Root directory for profiles.
            cli_overrides: CLI overrides.
            env_overrides: Environment variable overrides.

        Returns:
            Loaded and validated pipeline configuration.

        Raises:
            ConfigFileNotFoundError: Configuration file not found.
            ConfigValidationError: Configuration validation failed.
            UnknownProviderError: Unknown provider in configuration.
        """
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
            schema_contract_provider=self._schema_contract_provider,
            cli_overrides=cli_overrides,
            env_overrides=env_overrides,
            base_dir=None,
        )


# ============================================================================
# Module-level functions (use explicit provider or deprecated global state)
# ============================================================================


def get_pipeline_config(
    pipeline_id: str,
    *,
    schema_contract_provider: SchemaContractProviderABC | None = None,
    profile: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
    env_overrides: dict[str, Any] | None = None,
    base_dir: str | Path | None = None,
) -> PipelineConfig:
    """Загружает конфигурацию пайплайна по идентификатору.

    Args:
        pipeline_id: Идентификатор пайплайна (например, "chembl.activity").
        schema_contract_provider: Провайдер схем. Если None, используется
            глобальный провайдер (deprecated) или выбрасывается RuntimeError.
        profile: Имя профиля для применения.
        cli_overrides: Переопределения из CLI.
        env_overrides: Переопределения из переменных окружения.
        base_dir: Базовая директория для поиска конфигураций.

    Returns:
        PipelineConfig: Загруженная и валидированная конфигурация.

    Raises:
        ConfigFileNotFoundError: Файл конфигурации не найден.
        RuntimeError: SchemaContractProvider не инициализирован.
    """
    effective_provider = _resolve_schema_provider(schema_contract_provider)

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
        schema_contract_provider=effective_provider,
        cli_overrides=cli_overrides,
        env_overrides=env_overrides,
        base_dir=Path(base_dir) if base_dir is not None else None,
    )


def get_pipeline_config_from_path(
    config_path: str | Path,
    *,
    schema_contract_provider: SchemaContractProviderABC | None = None,
    profile: str | None = None,
    profiles_root: str | Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
    env_overrides: dict[str, Any] | None = None,
) -> PipelineConfig:
    """Загружает конфигурацию пайплайна из файла.

    Args:
        config_path: Путь к файлу конфигурации.
        schema_contract_provider: Провайдер схем. Если None, используется
            глобальный провайдер (deprecated) или выбрасывается RuntimeError.
        profile: Имя профиля для применения.
        profiles_root: Корневая директория профилей.
        cli_overrides: Переопределения из CLI.
        env_overrides: Переопределения из переменных окружения.

    Returns:
        PipelineConfig: Загруженная и валидированная конфигурация.

    Raises:
        ConfigFileNotFoundError: Файл конфигурации не найден.
        RuntimeError: SchemaContractProvider не инициализирован.
    """
    effective_provider = _resolve_schema_provider(schema_contract_provider)

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
        schema_contract_provider=effective_provider,
        cli_overrides=cli_overrides,
        env_overrides=env_overrides,
        base_dir=None,
    )


def _build_config(
    raw_config: dict[str, Any],
    *,
    config_path: Path,
    schema_contract_provider: SchemaContractProviderABC,
    cli_overrides: dict[str, Any] | None = None,
    env_overrides: dict[str, Any] | None = None,
    base_dir: Path | None = None,
) -> PipelineConfig:
    """Собирает PipelineConfig из сырых данных с применением overrides.

    Args:
        raw_config: Сырые данные конфигурации из YAML.
        config_path: Путь к файлу конфигурации.
        schema_contract_provider: Провайдер схем для заполнения полей.
        cli_overrides: Переопределения из CLI.
        env_overrides: Переопределения из переменных окружения.
        base_dir: Базовая директория для разрешения относительных путей.

    Returns:
        PipelineConfig: Собранная и валидированная конфигурация.
    """
    merged = resolve_env_placeholders(dict(raw_config))

    # Применяем overrides в порядке приоритета: env → CLI
    if env_overrides:
        env_values = resolve_env_placeholders(env_overrides)
        merged = apply_deep_merge(merged, env_values)
    if cli_overrides:
        cli_values = resolve_env_placeholders(cli_overrides)
        merged = apply_deep_merge(merged, cli_values)

    # Migration is handled here in the infrastructure layer before Pydantic validation.
    # This keeps the domain layer (PipelineConfig) clean from infrastructure dependencies.
    # The migration extracts provider_config from sources before provider validation.
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
    _populate_fields_from_schema(config, schema_contract_provider=schema_contract_provider)
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


# ============================================================================
# DEPRECATED: Global state for backward compatibility
# These will be removed in a future release. Pass schema_contract_provider
# explicitly to get_pipeline_config() and get_pipeline_config_from_path().
# ============================================================================

_SCHEMA_CONTRACT_PROVIDER: SchemaContractProviderABC | None = None


def _resolve_schema_provider(
    explicit_provider: SchemaContractProviderABC | None,
) -> SchemaContractProviderABC:
    """Resolve the schema provider to use, with deprecation warning for global state.

    Args:
        explicit_provider: Explicitly provided schema contract provider.

    Returns:
        The provider to use (explicit or global fallback).

    Raises:
        RuntimeError: If no provider is available.
    """
    if explicit_provider is not None:
        return explicit_provider

    # Fallback to global state (deprecated)
    if _SCHEMA_CONTRACT_PROVIDER is not None:
        warnings.warn(
            "Using global SchemaContractProvider is deprecated. "
            "Pass schema_contract_provider explicitly to get_pipeline_config() "
            "or get_pipeline_config_from_path(). "
            "Global state will be removed in a future release.",
            DeprecationWarning,
            stacklevel=4,
        )
        return _SCHEMA_CONTRACT_PROVIDER

    raise RuntimeError(
        "SchemaContractProvider not initialized. "
        "Pass schema_contract_provider parameter explicitly or "
        "call set_schema_contract_provider() for legacy compatibility."
    )


def set_schema_contract_provider(provider: SchemaContractProviderABC) -> None:
    """Set the global schema contract provider.

    .. deprecated::
        Global state injection is deprecated. Pass schema_contract_provider
        explicitly to get_pipeline_config() and get_pipeline_config_from_path()
        instead. This function will be removed in a future release.

    Args:
        provider: Configured SchemaContractProviderABC instance.

    Example:
        >>> from bioetl.application.services import SchemaContractProviderImpl
        >>> from bioetl.domain.schemas.registry import get_default_schema_registry
        >>> provider = SchemaContractProviderImpl(get_default_schema_registry())
        >>> set_schema_contract_provider(provider)  # deprecated
    """
    warnings.warn(
        "set_schema_contract_provider() is deprecated. "
        "Pass schema_contract_provider explicitly to get_pipeline_config() "
        "or get_pipeline_config_from_path(). "
        "This function will be removed in a future release.",
        DeprecationWarning,
        stacklevel=2,
    )
    global _SCHEMA_CONTRACT_PROVIDER  # noqa: PLW0603
    _SCHEMA_CONTRACT_PROVIDER = provider


def get_schema_contract_provider() -> SchemaContractProviderABC | None:
    """Get the current schema contract provider.

    .. deprecated::
        Global state access is deprecated. Use explicit provider injection instead.

    Returns:
        The configured schema contract provider, or None if not set.
    """
    warnings.warn(
        "get_schema_contract_provider() is deprecated. "
        "Use explicit provider injection instead. "
        "This function will be removed in a future release.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _SCHEMA_CONTRACT_PROVIDER


def clear_schema_contract_provider() -> None:
    """Clear the global schema contract provider (for testing).

    .. deprecated::
        Global state management is deprecated.

    This resets the provider to None, useful for test isolation.
    """
    warnings.warn(
        "clear_schema_contract_provider() is deprecated. "
        "Use explicit provider injection instead. "
        "This function will be removed in a future release.",
        DeprecationWarning,
        stacklevel=2,
    )
    global _SCHEMA_CONTRACT_PROVIDER  # noqa: PLW0603
    _SCHEMA_CONTRACT_PROVIDER = None


def reset_schema_contract_provider() -> None:
    """Reset the schema contract provider (for testing purposes).

    .. deprecated::
        Use clear_schema_contract_provider() instead.
        This function is kept for backward compatibility.
    """
    warnings.warn(
        "reset_schema_contract_provider() is deprecated. "
        "Use explicit provider injection instead. "
        "This function will be removed in a future release.",
        DeprecationWarning,
        stacklevel=2,
    )
    _clear_provider_internal()


def _clear_provider_internal() -> None:
    """Internal function to clear provider without deprecation warning.

    Used for test cleanup and internal state management.
    """
    global _SCHEMA_CONTRACT_PROVIDER  # noqa: PLW0603
    _SCHEMA_CONTRACT_PROVIDER = None


def _set_provider_internal(provider: SchemaContractProviderABC) -> None:
    """Internal function to set provider without deprecation warning.

    Used for backward compatibility in container bootstrap.
    Will be removed when global state is fully deprecated.
    """
    global _SCHEMA_CONTRACT_PROVIDER  # noqa: PLW0603
    _SCHEMA_CONTRACT_PROVIDER = provider


def create_schema_contract_loader(
    schema_contract_provider: SchemaContractProviderABC | None = None,
) -> SchemaContractLoader:
    """Create a SchemaContractLoader with the given or global provider.

    .. deprecated::
        This factory function is deprecated. Use dependency injection
        via CompositionRoot.create_schema_contract_loader() instead,
        or instantiate SchemaContractLoader directly with an explicit provider.

    Args:
        schema_contract_provider: Provider for schema contracts.
            If None, falls back to global state (deprecated).

    Returns:
        Configured SchemaContractLoader instance.

    Raises:
        RuntimeError: If no provider is available.

    Example (deprecated):
        >>> loader = create_schema_contract_loader()
        >>> config = loader.get_pipeline_config("chembl.activity")

    Preferred (DI approach):
        >>> from bioetl.interfaces.composition_root import get_composition_root
        >>> root = get_composition_root()
        >>> loader = root.create_schema_contract_loader()
    """
    warnings.warn(
        "create_schema_contract_loader() is deprecated. "
        "Use CompositionRoot.create_schema_contract_loader() "
        "or instantiate SchemaContractLoader directly with an explicit provider. "
        "This function will be removed in a future release.",
        DeprecationWarning,
        stacklevel=2,
    )
    effective_provider = _resolve_schema_provider(schema_contract_provider)
    return SchemaContractLoader(effective_provider)


def _populate_fields_from_schema(
    config: PipelineConfig,
    *,
    schema_contract_provider: SchemaContractProviderABC,
) -> None:
    """Populate config.fields using provided schema contract provider.

    Args:
        config: Pipeline configuration to populate fields for.
        schema_contract_provider: Provider for schema contracts.

    Raises:
        ConfigValidationError: If schema is not registered or produces empty fields.
    """
    if config.fields:
        return

    schema_name = schema_contract_provider.get_output_schema_name(
        config.id,
        default_entity=config.entity_name,
    )

    try:
        fields = schema_contract_provider.get_field_configs(schema_name)
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
    """Пытается разрешить относительный путь к существующему файлу.

    Uses PathResolver to check path existence against multiple candidate
    root directories.

    Args:
        path_str: Input path string to resolve.
        config_path: Path to the configuration file (for relative resolution).
        base_dir: Optional base directory override.

    Returns:
        Resolved path if file exists, None otherwise.
    """
    from bioetl.infrastructure.files.path_resolver import PathResolver

    candidate = Path(path_str).expanduser()
    if candidate.is_absolute():
        # For absolute paths, just check existence
        resolver = PathResolver(candidate.parent)
        return resolver.resolve_existing(candidate.name)

    # Try resolving against each candidate root
    for root in _iter_candidate_roots(config_path=config_path, base_dir=base_dir):
        resolver = PathResolver(root)
        resolved = resolver.resolve_existing(candidate)
        if resolved is not None:
            return resolved
    return None


def _iter_candidate_roots(
    *,
    config_path: Path,
    base_dir: Path | None,
) -> Iterable[Path]:
    """Генерирует директории, относительно которых ищем входной файл.

    Yields directories in priority order:
    1. base_dir (if provided)
    2. Current working directory
    3. Config file's parent directory
    4. All parent directories of config file path

    Args:
        config_path: Path to the configuration file.
        base_dir: Optional base directory override.

    Yields:
        Unique candidate root directories for path resolution.
    """
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
    # Primary API (DI-based)
    "SchemaContractLoader",
    # Exceptions
    "ConfigFileNotFoundError",
    "UnknownProviderError",
    # Module-level functions (support explicit provider or deprecated global state)
    "get_pipeline_config",
    "get_pipeline_config_from_path",
    # Deprecated functions (for backward compatibility, will be removed)
    "create_schema_contract_loader",
    "set_schema_contract_provider",
    "get_schema_contract_provider",
    "clear_schema_contract_provider",
    "reset_schema_contract_provider",
    # Internal functions (for container/test use during transition)
    "_set_provider_internal",
    "_clear_provider_internal",
]
