"""Leaf provider-registry loading helpers with injected registration routine."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.composition.providers._registry_protocols import (
    ProviderRegistrarProtocol,
)


def _register_default_providers(registry: ProviderRegistrarProtocol) -> None:
    """Register providers using the canonical registration entrypoint."""
    from bioetl.composition.providers.registration import register_all_providers

    register_all_providers(registry=registry)


def _has_registered_providers(registry: ProviderRegistrarProtocol) -> bool:
    """Return whether the target registry currently contains providers."""
    return bool(registry.list_providers())


def load_provider_registry(
    registry: ProviderRegistrarProtocol,
    *,
    force: bool = False,
    register_providers: Callable[[ProviderRegistrarProtocol], None] | None = None,
) -> None:
    """Load and register all providers into the supplied registry."""
    register_fn = (
        register_providers
        if register_providers is not None
        else _register_default_providers
    )

    if _has_registered_providers(registry) and not force:
        return

    if force:
        registry.clear()

    register_fn(registry)


def ensure_provider_registry_loaded(
    registry: ProviderRegistrarProtocol,
    *,
    register_providers: Callable[[ProviderRegistrarProtocol], None] | None = None,
) -> None:
    """Ensure the supplied registry has been populated with providers."""
    if not get_provider_registry_loaded_status(registry):
        load_provider_registry(
            registry,
            register_providers=register_providers,
        )


def get_provider_registry_loaded_status(
    registry: ProviderRegistrarProtocol,
) -> bool:
    """Return current loaded status for the supplied registry."""
    return _has_registered_providers(registry)


def reset_provider_registry_loader(
    registry: ProviderRegistrarProtocol,
) -> None:
    """Reset loader state and clear the supplied registry. Testing only."""
    registry.clear()
