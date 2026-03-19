"""Provider loader module.

Ensures all providers are registered in ProviderRegistry.
Called from bootstrap.py for initialization.
"""

from __future__ import annotations

from bioetl.composition.providers._loading import (
    ensure_provider_registry_loaded,
    get_provider_registry_loaded_status,
    load_provider_registry,
    reset_provider_registry_loader,
)
from bioetl.composition.providers.provider_registry import get_default_provider_registry
from bioetl.composition.providers.registration import register_all_providers

__all__ = [
    "ensure_providers_loaded",
    "get_loaded_status",
    "load_providers",
    "reset_loader",
]

def load_providers(force: bool = False) -> None:
    """Load and register all providers.

    This function should be called once at application startup
    (e.g., in bootstrap.py) to initialize ProviderRegistry.

    Idempotent - repeated calls are safe (if force=False).

    Args:
        force: If True, re-register providers even if already loaded.
            Used in tests to reset state.

    Example:
        >>> from bioetl.composition.providers import load_providers
        >>> load_providers()
        >>> # Now ProviderRegistry is ready
        >>> from bioetl.composition.providers import ProviderRegistry
        >>> config = ProviderRegistry.get("chembl")

    """
    load_provider_registry(
        get_default_provider_registry(),
        force=force,
        register_providers=register_all_providers,
    )


def ensure_providers_loaded() -> None:
    """Ensure providers are loaded.

    Convenience function for use in places where ProviderRegistry
    must be initialized.
    """
    ensure_provider_registry_loaded(
        get_default_provider_registry(),
        register_providers=register_all_providers,
    )


def get_loaded_status() -> bool:
    """Return provider loading status.

    Returns:
        Loaded status.
    """
    return get_provider_registry_loaded_status(get_default_provider_registry())


def reset_loader() -> None:
    """Reset loading status. Only for tests."""
    reset_provider_registry_loader(get_default_provider_registry())


_LOADER_API = (get_loaded_status, reset_loader)
