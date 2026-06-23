"""Internal registry-store helpers for provider metadata."""

from __future__ import annotations

from bioetl.composition.providers._models import ProviderConfig


class ProviderStore:
    """Thread-safe-compatible provider configuration store."""

    def __init__(self, providers: dict[str, ProviderConfig] | None = None) -> None:
        self._providers = providers if providers is not None else {}

    def register(self, name: str, config: ProviderConfig) -> None:
        """Register or overwrite a provider config in the shared store."""
        self._providers[name] = config

    def get(self, name: str) -> ProviderConfig:
        """Return provider config or raise a KeyError with available options."""
        if name not in self._providers:
            available = ", ".join(sorted(self._providers.keys()))
            raise KeyError(f"Unknown provider: {name}. Available: {available}")
        return self._providers[name]

    def is_registered(self, name: str) -> bool:
        """Return whether a provider name is present in the shared store."""
        return name in self._providers

    def list_names(self) -> list[str]:
        """Return registered provider names in stable sorted order."""
        return sorted(self._providers.keys())

    def clear(self) -> None:
        """Clear all registered providers."""
        self._providers.clear()


def register_provider_config(
    providers: dict[str, ProviderConfig],
    name: str,
    config: ProviderConfig,
) -> None:
    """Register or overwrite a provider config (backward-compatible function)."""
    providers[name] = config


def get_provider_config(
    providers: dict[str, ProviderConfig],
    name: str,
) -> ProviderConfig:
    """Return provider config (backward-compatible function)."""
    if name not in providers:
        available = ", ".join(sorted(providers.keys()))
        raise KeyError(f"Unknown provider: {name}. Available: {available}")
    return providers[name]


def is_provider_registered(
    providers: dict[str, ProviderConfig],
    name: str,
) -> bool:
    """Return whether a provider name is present (backward-compatible function)."""
    return name in providers


def list_provider_names(providers: dict[str, ProviderConfig]) -> list[str]:
    """Return registered provider names (backward-compatible function)."""
    return sorted(providers.keys())
