"""Provider registry protocols for composition contracts."""

from __future__ import annotations

from typing import Protocol, Self

ProviderConfigRuntime = object


class SupportsDefaultRegistry(Protocol):
    @classmethod
    def _get_default(cls) -> Self:
        """Return the lazy default registry instance."""
        ...


class SupportsProviderStore(Protocol):
    _providers: dict[str, ProviderConfigRuntime]


class SupportsProviderRegistryStore(SupportsDefaultRegistry, Protocol):
    _store: SupportsProviderStore

    def register(self, name: str, config: ProviderConfigRuntime) -> None: ...

    def is_registered(self, name: str) -> bool: ...

    def list_providers(self) -> list[str]: ...

    def clear(self) -> None: ...
