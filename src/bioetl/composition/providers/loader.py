"""Retained bootstrap convenience seam for provider loading.

Wave 3 ownership classification: retain.

This module remains a thin bootstrap facade over ``_loading.py`` and routes the
default-registry path through ``_registry_resolution.py`` instead of owning
registry bootstrap logic directly.
"""

from __future__ import annotations

from typing import cast

from bioetl.composition.providers._loading import (
    ensure_provider_registry_loaded,
    get_provider_registry_loaded_status,
    load_provider_registry,
    reset_provider_registry_loader,
)
from bioetl.composition.providers._registry_protocols import (
    ProviderRegistrarProtocol,
)
from bioetl.composition.providers._registry_resolution import (
    resolve_provider_registry,
)

__all__ = [
    "ensure_providers_loaded",
    "get_loaded_status",
    "load_providers",
    "reset_loader",
]


def _get_loader_registry() -> ProviderRegistrarProtocol:
    """Resolve the canonical default provider registry for loader entrypoints."""
    return cast(ProviderRegistrarProtocol, resolve_provider_registry())


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
        _get_loader_registry(),
        force=force,
    )


def ensure_providers_loaded() -> None:
    """Ensure providers are loaded.

    Convenience function for use in places where ProviderRegistry
    must be initialized.
    """
    ensure_provider_registry_loaded(
        _get_loader_registry(),
    )


def get_loaded_status() -> bool:
    """Return provider loading status.

    Returns:
        Loaded status.
    """
    return get_provider_registry_loaded_status(_get_loader_registry())


def reset_loader() -> None:
    """Reset loading status. Only for tests."""
    reset_provider_registry_loader(_get_loader_registry())
