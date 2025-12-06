"""Loader for provider registry definitions from YAML configuration."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from bioetl.domain.clients.base.logging.contracts import LoggerAdapterABC
from bioetl.domain.provider_registry import (
    InMemoryProviderRegistry,
    MutableProviderRegistryABC,
    ProviderAlreadyRegisteredError,
)
from bioetl.domain.providers import ProviderDefinition, ProviderId
from bioetl.domain.provider_loader import ProviderLoaderProtocol
from bioetl.infrastructure.logging.factories import default_logger

DEFAULT_PROVIDERS_CONFIG_PATH = Path("configs/providers.yaml")


class ProviderRegistryLoaderError(Exception):
    """Base error for provider registry loading."""


class ProviderRegistryConfigNotFoundError(ProviderRegistryLoaderError):
    """Raised when provider registry config file is missing."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"Provider registry config not found: {path}")
        self.path = path


class ProviderRegistryValidationError(ProviderRegistryLoaderError):
    """Raised when provider registry config is invalid."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path


class ProviderRegistryEntry(BaseModel):
    """Single provider entry from registry config."""

    model_config = ConfigDict(extra="forbid")

    id: ProviderId
    module: str
    factory: str
    active: bool = True
    description: str | None = None


class ProviderRegistryConfig(BaseModel):
    """Root provider registry configuration."""

    model_config = ConfigDict(extra="forbid")

    providers: list[ProviderRegistryEntry]


class ProviderLoaderImpl(ProviderLoaderProtocol):
    """Loads provider registry entries and registers them dynamically."""

    def __init__(
        self,
        config_path: str | Path | None = None,
        *,
        logger: LoggerAdapterABC | None = None,
    ) -> None:
        self._config_path = (
            Path(config_path) if config_path else DEFAULT_PROVIDERS_CONFIG_PATH
        )
        self._logger = logger or default_logger()

    def load(
        self,
        *,
        registry: MutableProviderRegistryABC | None = None,
    ) -> list[ProviderDefinition]:
        """Load providers from YAML and register active entries."""

        registry_to_use = registry or InMemoryProviderRegistry()
        raw_config = self._load_config(self._config_path)
        try:
            config = ProviderRegistryConfig.model_validate(raw_config)
        except ValidationError as exc:
            raise ProviderRegistryValidationError(
                self._config_path,
                exc.__str__(),
            ) from exc

        registered: list[ProviderDefinition] = []
        for entry in config.providers:
            if not entry.active:
                self._logger.debug(
                    "Provider entry is disabled; skipping",
                    provider=entry.id.value,
                    module=entry.module,
                )
                continue
            definition = self._register_entry(entry, registry_to_use)
            if definition:
                registered.append(definition)
        return registered

    def load_registry(
        self, *, registry: MutableProviderRegistryABC | None = None
    ) -> MutableProviderRegistryABC:
        """Load providers and return populated registry (Protocol compatibility)."""

        registry_to_use = registry or InMemoryProviderRegistry()
        self.load(registry=registry_to_use)
        return registry_to_use

    def _register_entry(
        self,
        entry: ProviderRegistryEntry,
        registry: MutableProviderRegistryABC,
    ) -> ProviderDefinition | None:
        try:
            module = importlib.import_module(entry.module)
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.error(
                "Failed to import provider module",
                provider=entry.id.value,
                module=entry.module,
                error=str(exc),
            )
            return None

        factory: Any = getattr(module, entry.factory, None)
        if factory is None:
            self._logger.error(
                "Provider factory not found",
                provider=entry.id.value,
                module=entry.module,
                factory=entry.factory,
            )
            return None

        try:
            definition = factory()
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.error(
                "Provider factory invocation failed",
                provider=entry.id.value,
                module=entry.module,
                factory=entry.factory,
                error=str(exc),
            )
            return None

        if not isinstance(definition, ProviderDefinition):
            self._logger.error(
                "Factory returned unexpected type",
                provider=entry.id.value,
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
                provider=entry.id.value,
                module=entry.module,
            )
            return registry.get_provider(definition.id)
        return definition

    def _load_config(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise ProviderRegistryConfigNotFoundError(path)

        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
        return data


def load_provider_registry(
    *,
    config_path: str | Path | None = None,
    logger: LoggerAdapterABC | None = None,
    registry: MutableProviderRegistryABC | None = None,
) -> MutableProviderRegistryABC:
    """Utility to load provider registry and return the populated instance."""

    loader = ProviderLoaderImpl(config_path=config_path, logger=logger)
    registry_to_use = registry or InMemoryProviderRegistry()
    return loader.load_registry(registry=registry_to_use)


def create_provider_loader(
    *,
    config_path: str | Path | None = None,
    logger: LoggerAdapterABC | None = None,
) -> ProviderLoaderProtocol:
    """Factory for ProviderLoaderProtocol implementations."""

    return ProviderLoaderImpl(config_path=config_path, logger=logger)


ProviderRegistryLoader = ProviderLoaderImpl

__all__ = [
    "ProviderLoaderImpl",
    "ProviderRegistryLoader",
    "create_provider_loader",
    "load_provider_registry",
    "ProviderRegistryLoaderError",
    "ProviderRegistryConfigNotFoundError",
    "ProviderRegistryValidationError",
]
