"""Provider-registry structural contracts (ADR-058)."""

from __future__ import annotations

from typing import Protocol, Self

ProviderConfig = object


class SupportsDefaultRegistry(Protocol):
    @classmethod
    def _get_default(cls) -> Self:
        """Return the lazy default registry instance."""
        ...


class SupportsProviderStore(Protocol):
    _providers: dict[str, ProviderConfig]


class SupportsProviderRegistryStore(SupportsDefaultRegistry, Protocol):
    _store: SupportsProviderStore

    def register(self, name: str, config: ProviderConfig) -> None: ...

    def is_registered(self, name: str) -> bool: ...

    def list_providers(self) -> list[str]: ...

    def clear(self) -> None: ...
