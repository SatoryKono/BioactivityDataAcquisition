"""Internal registry-store helpers for provider metadata."""

from __future__ import annotations

from bioetl.composition.providers._models import ProviderConfig


def register_provider_config(
    providers: dict[str, ProviderConfig],
    name: str,
    config: ProviderConfig,
) -> None:
    """Register or overwrite a provider config in the shared store."""
    providers[name] = config


def get_provider_config(
    providers: dict[str, ProviderConfig],
    name: str,
) -> ProviderConfig:
    """Return provider config or raise a KeyError with available options."""
    if name not in providers:
        available = ", ".join(sorted(providers.keys()))
        raise KeyError(f"Unknown provider: {name}. Available: {available}")
    return providers[name]


def is_provider_registered(
    providers: dict[str, ProviderConfig],
    name: str,
) -> bool:
    """Return whether a provider name is present in the shared store."""
    return name in providers


def list_provider_names(providers: dict[str, ProviderConfig]) -> list[str]:
    """Return registered provider names in stable sorted order."""
    return sorted(providers.keys())
