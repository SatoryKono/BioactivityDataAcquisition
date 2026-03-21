"""Neutral protocol contracts shared by provider-registry helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.composition.providers._models import ProviderConfig


class ProviderRegistrarProtocol(Protocol):
    """Minimal registry contract for provider registration assembly."""

    def register(self, name: str, config: ProviderConfig) -> None:
        """Register a provider config."""
        ...

    def is_registered(self, name: str) -> bool:
        """Return whether the provider is already registered."""
        ...

    def list_providers(self) -> list[str]:
        """List registered providers."""
        ...

    def clear(self) -> None:
        """Clear all registered providers."""
        ...
