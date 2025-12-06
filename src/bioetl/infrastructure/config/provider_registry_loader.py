"""Infrastructure loader for provider registry configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

DEFAULT_CONFIGS_ROOT = Path("configs")
DEFAULT_PROVIDERS_REGISTRY_PATH = DEFAULT_CONFIGS_ROOT / "providers.yaml"

__all__ = [
    "DEFAULT_PROVIDERS_REGISTRY_PATH",
    "ProviderNotConfiguredError",
    "ProviderRegistryError",
    "ProviderRegistryFormatError",
    "ProviderRegistryNotFoundError",
    "clear_provider_registry_cache",
    "ensure_provider_known",
]


class ProviderRegistryError(Exception):
    """Base error for provider registry issues."""


class ProviderRegistryNotFoundError(ProviderRegistryError):
    """Registry file is missing."""

    def __init__(self, registry_path: Path) -> None:
        self.registry_path = registry_path
        super().__init__(f"Providers registry not found: {registry_path}")


class ProviderRegistryFormatError(ProviderRegistryError):
    """Registry file has invalid structure."""

    def __init__(self, registry_path: Path, message: str) -> None:
        self.registry_path = registry_path
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


class ProviderRegistryEntryModel(BaseModel):
    """Single provider entry from providers.yaml."""

    model_config = ConfigDict(extra="forbid")

    id: str
    module: str
    factory: str
    active: bool = True
    description: str | None = None


class ProviderRegistryModel(BaseModel):
    """Validated providers.yaml content."""

    model_config = ConfigDict(extra="forbid")

    providers: list[ProviderRegistryEntryModel] = []


def ensure_provider_known(provider: str, *, registry_path: Path | None = None) -> str:
    """Validate that provider exists in registry and return it back.

    Если задан явный путь к реестру, игнорируем рантайм-регистрации
    (нужно для строгой валидации конфигов в тестах и CLI).
    """

    path = registry_path or DEFAULT_PROVIDERS_REGISTRY_PATH
    registry = _load_provider_registry(path)
    registered_ids = {entry.id for entry in registry.providers if entry.active}

    if provider in registered_ids:
        return provider

    raise ProviderNotConfiguredError(provider, path)


def clear_provider_registry_cache() -> None:
    """Reset cached registry content (used in tests)."""

    _load_provider_registry.cache_clear()


def _read_registry_data(registry_path: Path) -> Any:
    if not registry_path.exists():
        raise ProviderRegistryNotFoundError(registry_path)

    with registry_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


@lru_cache(maxsize=None)
def _load_provider_registry(registry_path: Path) -> ProviderRegistryModel:
    data: Any = _read_registry_data(registry_path)
    try:
        return ProviderRegistryModel.model_validate(data)
    except ValidationError as exc:
        raise ProviderRegistryFormatError(registry_path, exc.__str__()) from exc
