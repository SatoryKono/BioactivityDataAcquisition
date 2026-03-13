"""Provider loader module.

Ensures all providers are registered in ProviderRegistry.
Called from bootstrap.py for initialization.
"""

from __future__ import annotations

from bioetl.composition.providers.provider_registry import ProviderRegistry
from bioetl.composition.providers.registration import register_all_providers

__all__ = [
    "ensure_providers_loaded",
    "get_loaded_status",
    "load_providers",
    "reset_loader",
]

_loaded = False


def _has_registered_providers() -> bool:
    """Return whether the provider registry currently contains providers."""
    return bool(ProviderRegistry.list_providers())


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
    global _loaded

    if get_loaded_status() and not force:
        return

    if _has_registered_providers() and not force:
        _loaded = True
        return

    if force:
        # Clear registry before re-registration
        ProviderRegistry.clear()

    # Explicit registration of all providers
    register_all_providers()

    _loaded = _has_registered_providers()


def ensure_providers_loaded() -> None:
    """Ensure providers are loaded.

    Convenience function for use in places where ProviderRegistry
    must be initialized.
    """
    if not get_loaded_status():
        load_providers()


def get_loaded_status() -> bool:
    """Return provider loading status.

    Returns:
        Loaded status.
    """
    return _loaded and _has_registered_providers()


def reset_loader() -> None:
    """Reset loading status. Only for tests."""
    global _loaded
    _loaded = False
    ProviderRegistry.clear()


_LOADER_API = (get_loaded_status, reset_loader)
