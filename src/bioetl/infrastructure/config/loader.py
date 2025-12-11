"""Pipeline configuration loader.

This module provides pipeline configuration loading functionality with support
for dependency injection of schema contract providers.

Usage (DI approach - recommended):
    >>> from bioetl.interfaces.composition_root import get_composition_root
    >>> root = get_composition_root()
    >>> loader = root.create_schema_contract_loader()
    >>> config = loader.get_pipeline_config("chembl.activity")

Alternative (explicit provider):
    >>> from bioetl.infrastructure.config.loader import get_pipeline_config
    >>> config = get_pipeline_config(
    ...     "chembl.activity", schema_contract_provider=provider
    ... )
"""

from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from bioetl.domain.configs import PipelineConfig
from bioetl.domain.errors import ConfigError, ConfigValidationError
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.transform.merge import apply_deep_merge
from bioetl.infrastructure.config.env import resolve_env_placeholders
from bioetl.infrastructure.config.migration import ConfigMigrator
from bioetl.infrastructure.config.provider_registry import (
    ProviderNotConfiguredError,
    ProviderRegistryError,
    ensure_provider_known,
)
from bioetl.infrastructure.config.sources import (
    get_yaml_for_pipeline,
    get_yaml_from_path,
)

# -----------------------------------------------------------------------------
# Backward-compatible provider context (no global mutable state)
# -----------------------------------------------------------------------------

_SCHEMA_CONTRACT_CTX: ContextVar[
    SchemaContractProviderABC | None
] = ContextVar("_schema_contract_ctx", default=None)


def set_schema_contract_provider(provider: SchemaContractProviderABC | None) -> None:
    """Inject schema contract provider into context (legacy compatibility)."""
    if provider is None:
        raise ValueError("provider must not be None")
    _SCHEMA_CONTRACT_CTX.set(provider)


def get_schema_contract_provider() -> SchemaContractProviderABC | None:
    """Return schema contract provider from context if set."""
    return _SCHEMA_CONTRACT_CTX.get()


def clear_schema_contract_provider() -> None:
    """Clear schema contract provider from context."""
    _SCHEMA_CONTRACT_CTX.set(None)


def reset_schema_contract_provider() -> None:
    """Alias for clearing provider (kept for backward compatibility)."""
    clear_schema_contract_provider()


class ConfigFileNotFoundError(ConfigError):
    """Configuration file not found."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"Config file not found: {path}")
        self.path = path


class UnknownProviderError(ConfigError):
    """Unknown provider."""

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
# Module-level functions (require explicit provider)
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
    """Load pipeline configuration by identifier.

    Args:
        pipeline_id: Pipeline identifier (e.g., "chembl.activity").
        schema_contract_provider: Schema provider (required).
        profile: Profile name to apply.
        cli_overrides: CLI overrides.
        env_overrides: Environment variable overrides.
        base_dir: Base directory for configuration search.

    Returns:
        PipelineConfig: Loaded and validated configuration.

    Raises:
        ConfigFileNotFoundError: Configuration file not found.
        ValueError: If schema_contract_provider is not provided.
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
    """Load pipeline configuration from file.

    Args:
        config_path: Path to configuration file.
        schema_contract_provider: Schema provider (required).
        profile: Profile name to apply.
        profiles_root: Profiles root directory.
        cli_overrides: CLI overrides.
        env_overrides: Environment variable overrides.

    Returns:
        PipelineConfig: Loaded and validated configuration.

    Raises:
        ConfigFileNotFoundError: Configuration file not found.
        ValueError: If schema_contract_provider is not provided.
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
    """Build PipelineConfig from raw data with applied overrides.

    Args:
        raw_config: Raw configuration data from YAML.
        config_path: Path to configuration file.
        schema_contract_provider: Schema provider for populating fields.
        cli_overrides: CLI overrides.
        env_overrides: Environment variable overrides.
        base_dir: Base directory for resolving relative paths.

    Returns:
        PipelineConfig: Built and validated configuration.
    """
    merged = resolve_env_placeholders(dict(raw_config))

    # Apply overrides in priority order: env → CLI
    if env_overrides:
        env_values = resolve_env_placeholders(env_overrides)
        merged = apply_deep_merge(merged, env_values)
    if cli_overrides:
        cli_values = resolve_env_placeholders(cli_overrides)
        merged = apply_deep_merge(merged, cli_values)

    # Migration is handled here in the infrastructure layer before Pydantic
    # validation. This keeps the domain layer (PipelineConfig) clean from
    # infrastructure dependencies. The migration extracts provider_config
    # from sources before provider validation.
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
    _populate_fields_from_schema(
        config, schema_contract_provider=schema_contract_provider
    )
    return config


def _ensure_provider_registered(provider_id: str) -> None:
    """Check provider existence in registry before schema validation."""

    try:
        ensure_provider_known(provider_id)
    except ProviderNotConfiguredError as exc:
        raise UnknownProviderError(provider_id) from exc
    except ProviderRegistryError as exc:
        raise ConfigError(
            f"Failed to verify provider '{provider_id}' against registry: {exc}"
        ) from exc


def _resolve_schema_provider(
    explicit_provider: SchemaContractProviderABC | None,
) -> SchemaContractProviderABC:
    """Resolve schema provider from explicit arg or global injection."""
    if explicit_provider is not None:
        return explicit_provider

    provider = get_schema_contract_provider()
    if provider is None:
        raise RuntimeError(
            "SchemaContractProvider not initialized. "
            "Bootstrap the application or call set_schema_contract_provider()."
        )
    return provider


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
        try:
            from bioetl.domain.schemas.fields import build_field_configs_from_schema
            from bioetl.domain.schemas.registry import create_default_schema_registry

            registry = create_default_schema_registry()
            schema = registry.get_schema(schema_name)
            fields = build_field_configs_from_schema(schema)
        except Exception:
            raise ConfigValidationError(
                f"Schema '{schema_name}' is not registered for pipeline '{config.id}'"
            ) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
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
    """Check local file accessibility for CSV/id-only modes."""

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
    """Try to resolve relative path to existing file.

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
    """Generate directories relative to which we search for input file.

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
    # Module-level functions (require explicit provider)
    "get_pipeline_config",
    "get_pipeline_config_from_path",
]
