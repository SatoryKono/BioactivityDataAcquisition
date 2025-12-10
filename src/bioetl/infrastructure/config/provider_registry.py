"""Unified provider registry loader from YAML configuration.

This module provides a single source of truth for loading and validating
provider registry configuration from providers.yaml.

It combines functionality from:
- Provider validation and caching (ensure_provider_known, etc.)
- Dynamic provider loading via importlib (ProviderLoaderImpl)
"""

from __future__ import annotations

import importlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError
import yaml

from bioetl.domain.configs import HttpClientSettings
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.provider_registry import (
    InMemoryProviderRegistry,
    ProviderAlreadyRegisteredError,
    ProviderRegistryABC,
    ProviderRegistryLoaderABC,
)
from bioetl.domain.providers import ProviderDefinition, ProviderId
from bioetl.infrastructure.clients.chembl.provider import register_chembl_provider
from bioetl.infrastructure.observability.factories import default_logging_port

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CONFIGS_ROOT = Path("configs")
DEFAULT_PROVIDERS_REGISTRY_PATH = DEFAULT_CONFIGS_ROOT / "providers.yaml"
DEFAULT_PROVIDERS_CONFIG_PATH = DEFAULT_PROVIDERS_REGISTRY_PATH  # Alias for compatibility


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ProviderRegistryError(Exception):
    """Base error for provider registry issues."""


class ProviderRegistryNotFoundError(ProviderRegistryError):
    """Registry file is missing."""

    def __init__(self, registry_path: Path) -> None:
        self.registry_path = registry_path
        self.path = registry_path  # Alias for compatibility
        super().__init__(f"Providers registry not found: {registry_path}")


class ProviderRegistryFormatError(ProviderRegistryError):
    """Registry file has invalid structure."""

    def __init__(self, registry_path: Path, message: str) -> None:
        self.registry_path = registry_path
        self.path = registry_path  # Alias for compatibility
        super().__init__(f"{registry_path}: {message}")


class ProviderNotConfiguredError(ProviderRegistryError):
    """Requested provider is absent in registry."""

    def __init__(self, provider: str, registry_path: Path) -> None:
        self.provider = provider
        self.registry_path = registry_path
        super().__init__(
            (
                "Provider '{provider}' is not configured in providers config "
                "{registry_path}"
            ).format(provider=provider, registry_path=registry_path)
        )


# Aliases for backward compatibility with clients/provider_registry_loader.py
ProviderRegistryLoaderError = ProviderRegistryError
ProviderRegistryConfigNotFoundError = ProviderRegistryNotFoundError
ProviderRegistryValidationError = ProviderRegistryFormatError


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class ProviderRegistryEntryModel(BaseModel):
    """Single provider entry from providers.yaml.

    This is the canonical model for provider registry entries.
    Supports both string IDs (for validation) and ProviderId enum (for loading).
    """

    model_config = ConfigDict(extra="forbid")

    id: str | ProviderId
    module: str
    factory: str
    active: bool = True
    description: str | None = None
    http_client: HttpClientSettings | None = None


# Alias for backward compatibility
ProviderRegistryEntryConfig = ProviderRegistryEntryModel


class ProviderRegistryConfig(BaseModel):
    """Root provider registry configuration (validated providers.yaml content)."""

    model_config = ConfigDict(extra="forbid")

    providers: list[ProviderRegistryEntryModel] = []


# Alias for backward compatibility
ProviderRegistryModel = ProviderRegistryConfig


# ---------------------------------------------------------------------------
# YAML Loading (with caching)
# ---------------------------------------------------------------------------


def _read_registry_data(registry_path: Path) -> Any:
    """Read raw YAML data from registry file."""
    if not registry_path.exists():
        raise ProviderRegistryNotFoundError(registry_path)

    with registry_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


@lru_cache(maxsize=None)
def _load_provider_registry(registry_path: Path) -> ProviderRegistryConfig:
    """Load and validate provider registry from YAML (cached)."""
    data: Any = _read_registry_data(registry_path)
    try:
        return ProviderRegistryConfig.model_validate(data)
    except ValidationError as exc:
        raise ProviderRegistryFormatError(registry_path, str(exc)) from exc


def clear_provider_registry_cache() -> None:
    """Reset cached registry content (used in tests)."""
    _load_provider_registry.cache_clear()


# ---------------------------------------------------------------------------
# Provider Validation
# ---------------------------------------------------------------------------


def ensure_provider_known(provider: str, *, registry_path: Path | None = None) -> str:
    """Validate that provider exists in registry and return it back.

    Args:
        provider: Provider ID to validate
        registry_path: Optional path to providers.yaml

    Returns:
        The provider ID if valid

    Raises:
        ProviderNotConfiguredError: If provider is not in registry
        ProviderRegistryNotFoundError: If registry file is missing
        ProviderRegistryFormatError: If registry has invalid structure
    """
    path = registry_path or DEFAULT_PROVIDERS_REGISTRY_PATH
    registry = _load_provider_registry(path)

    # Extract ID as string for comparison
    registered_ids = set()
    for entry in registry.providers:
        if entry.active:
            entry_id = entry.id.value if isinstance(entry.id, ProviderId) else entry.id
            registered_ids.add(entry_id)

    if provider in registered_ids:
        return provider

    raise ProviderNotConfiguredError(provider, path)


# ---------------------------------------------------------------------------
# Dynamic Provider Loader
# ---------------------------------------------------------------------------


class ProviderLoaderImpl(ProviderRegistryLoaderABC):
    """Loads provider registry entries and registers them dynamically.

    This class loads provider definitions from providers.yaml and dynamically
    imports the specified modules to invoke factory functions.
    """

    def __init__(
        self,
        config_path: str | Path | None = None,
        *,
        logger: LoggingPortABC | None = None,
    ) -> None:
        self._config_path = (
            Path(config_path) if config_path else DEFAULT_PROVIDERS_CONFIG_PATH
        )
        self._logger = logger or default_logging_port()

    def get_providers(
        self,
        *,
        registry: ProviderRegistryABC | None = None,
    ) -> list[ProviderDefinition]:
        """Get providers from YAML and register active entries."""
        registry_to_use = registry or InMemoryProviderRegistry()
        raw_config = self._load_config(self._config_path)
        try:
            config = ProviderRegistryConfig.model_validate(raw_config)
        except ValidationError as exc:
            raise ProviderRegistryFormatError(
                self._config_path,
                str(exc),
            ) from exc

        registered: list[ProviderDefinition] = []
        for entry in config.providers:
            if not entry.active:
                entry_id = (
                    entry.id.value if isinstance(entry.id, ProviderId) else entry.id
                )
                self._logger.debug(
                    "Provider entry is disabled; skipping",
                    provider=entry_id,
                    module=entry.module,
                )
                continue
            definition = self._register_entry(entry, registry_to_use)
            if definition:
                registered.append(definition)

        # Fallback to builtin ChEMBL provider if nothing was registered (defensive).
        if not registered:
            builtin = register_chembl_provider()
            try:
                registry_to_use.register_provider(builtin)
            except ProviderAlreadyRegisteredError:
                self._logger.debug(
                    "Provider already registered; reusing existing definition",
                    provider=builtin.id.value,
                    module="bioetl.infrastructure.clients.chembl.provider",
                )
                registered.append(registry_to_use.get_provider(builtin.id))
            else:
                registered.append(builtin)
        return registered

    def load(
        self, *, registry: ProviderRegistryABC | None = None
    ) -> list[ProviderDefinition]:
        """Backward-compatible alias for get_providers expected by tests and callers."""
        return self.get_providers(registry=registry)

    def get_registry(
        self, *, registry: ProviderRegistryABC | None = None
    ) -> ProviderRegistryABC:
        """Get providers and return populated registry (Protocol compatibility)."""
        registry_to_use = registry or InMemoryProviderRegistry()
        self.get_providers(registry=registry_to_use)
        return registry_to_use

    def _register_entry(
        self,
        entry: ProviderRegistryEntryModel,
        registry: ProviderRegistryABC,
    ) -> ProviderDefinition | None:
        entry_id = entry.id.value if isinstance(entry.id, ProviderId) else entry.id

        try:
            module = importlib.import_module(entry.module)
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.error(
                "Failed to import provider module",
                provider=entry_id,
                module=entry.module,
                error=str(exc),
            )
            return None

        factory: Any = getattr(module, entry.factory, None)
        if factory is None:
            self._logger.error(
                "Provider factory not found",
                provider=entry_id,
                module=entry.module,
                factory=entry.factory,
            )
            return None

        try:
            definition = factory(http_client=entry.http_client)
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.error(
                "Provider factory invocation failed",
                provider=entry_id,
                module=entry.module,
                factory=entry.factory,
                error=str(exc),
            )
            return None

        if not isinstance(definition, ProviderDefinition):
            self._logger.error(
                "Factory returned unexpected type",
                provider=entry_id,
                module=entry.module,
                factory=entry.factory,
                returned_type=type(definition).__name__,
            )
            return None

        try:
            registry.register_provider(definition)
        except ProviderAlreadyRegisteredError:
            self._logger.debug(
                "Provider already registered; reusing existing definition",
                provider=entry_id,
                module=entry.module,
            )
            return registry.get_provider(definition.id)
        return definition

    def _load_config(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise ProviderRegistryNotFoundError(path)

        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
        return data


# Alias for backward compatibility
ProviderRegistryLoader = ProviderLoaderImpl


# ---------------------------------------------------------------------------
# Factory Functions
# ---------------------------------------------------------------------------


def get_provider_registry(
    *,
    config_path: str | Path | None = None,
    logger: LoggingPortABC | None = None,
    registry: ProviderRegistryABC | None = None,
) -> ProviderRegistryABC:
    """Utility to return populated provider registry."""
    loader = default_provider_registry_loader(
        config_path=config_path,
        logger=logger,
    )
    registry_to_use = registry or InMemoryProviderRegistry()
    return loader.get_registry(registry=registry_to_use)


def create_provider_loader(
    *,
    config_path: str | Path | None = None,
    logger: LoggingPortABC | None = None,
) -> ProviderRegistryLoaderABC:
    """Factory for ProviderLoaderProtocol implementations."""
    return ProviderLoaderImpl(config_path=config_path, logger=logger)


def default_provider_registry_loader(
    *,
    config_path: str | Path | None = None,
    logger: LoggingPortABC | None = None,
) -> ProviderRegistryLoaderABC:
    """Default factory for provider registry loader."""
    return ProviderLoaderImpl(config_path=config_path, logger=logger)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # Constants
    "DEFAULT_CONFIGS_ROOT",
    "DEFAULT_PROVIDERS_REGISTRY_PATH",
    "DEFAULT_PROVIDERS_CONFIG_PATH",
    # Exceptions
    "ProviderRegistryError",
    "ProviderRegistryNotFoundError",
    "ProviderRegistryFormatError",
    "ProviderNotConfiguredError",
    # Backward-compatible exception aliases
    "ProviderRegistryLoaderError",
    "ProviderRegistryConfigNotFoundError",
    "ProviderRegistryValidationError",
    # Models
    "ProviderRegistryEntryModel",
    "ProviderRegistryEntryConfig",  # Alias
    "ProviderRegistryConfig",
    "ProviderRegistryModel",  # Alias
    # Loader class
    "ProviderLoaderImpl",
    "ProviderRegistryLoader",  # Alias
    # Validation functions
    "ensure_provider_known",
    "clear_provider_registry_cache",
    # Factory functions
    "get_provider_registry",
    "create_provider_loader",
    "default_provider_registry_loader",
]
