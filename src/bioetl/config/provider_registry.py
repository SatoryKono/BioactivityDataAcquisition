"""Provider registry loader based on configuration YAML."""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache
from typing import Any

import yaml

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
            f"Provider '{provider}' is not configured in registry {registry_path}"
        )


def ensure_provider_known(provider: str, *, registry_path: Path | None = None) -> str:
    """Validate that provider exists in registry and return it back."""

    path = registry_path or DEFAULT_PROVIDERS_REGISTRY_PATH
    registry = _load_provider_registry(path)
    if provider not in registry:
        raise ProviderNotConfiguredError(provider, path)
    return provider


def clear_provider_registry_cache() -> None:
    """Reset cached registry content (used in tests)."""

    _load_provider_registry.cache_clear()


def _read_registry_data(registry_path: Path) -> Any:
    if not registry_path.exists():
        raise ProviderRegistryNotFoundError(registry_path)

    with registry_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _parse_registry_data(data: Any, registry_path: Path) -> set[str]:
    if not isinstance(data, dict):
        raise ProviderRegistryFormatError(registry_path, "YAML root must be a mapping")

    providers = data.get("providers")
    if providers is None:
        return set()
    if not isinstance(providers, list):
        raise ProviderRegistryFormatError(
            registry_path,
            "'providers' must be a list",
        )

    return _collect_provider_ids(providers, registry_path)


def _collect_provider_ids(providers: list[Any], registry_path: Path) -> set[str]:
    registry: set[str] = set()
    for provider in providers:
        registry.add(_normalize_provider_entry(provider, registry_path))
    return registry


def _normalize_provider_entry(provider: Any, registry_path: Path) -> str:
    if isinstance(provider, str):
        return provider
    if isinstance(provider, dict):
        provider_id = provider.get("id")
        if provider_id is None:
            raise ProviderRegistryFormatError(
                registry_path,
                "Provider entry must have 'id' field",
            )
        return str(provider_id)
    raise ProviderRegistryFormatError(
        registry_path,
        (
            "Provider entry must be string or dict, "
            f"got {type(provider).__name__}"
        ),
    )


@lru_cache(maxsize=None)
def _load_provider_registry(registry_path: Path) -> set[str]:
    data: Any = _read_registry_data(registry_path)
    return _parse_registry_data(data, registry_path)
