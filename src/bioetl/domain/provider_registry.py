"""Provider registry domain abstractions (stub - module was removed)."""

# This module was removed. Import stub from tests when available.
# The stub is automatically patched via pytest_configure in tests/conftest.py

try:
    from tests.fixtures import provider_registry_stub

    # Re-export all symbols from stub
    ProviderRegistryError = provider_registry_stub.ProviderRegistryError
    ProviderNotRegisteredError = provider_registry_stub.ProviderNotRegisteredError
    ProviderAlreadyRegisteredError = provider_registry_stub.ProviderAlreadyRegisteredError
    ProviderRegistryABC = provider_registry_stub.ProviderRegistryABC
    ProviderRegistryLoaderABC = provider_registry_stub.ProviderRegistryLoaderABC
    InMemoryProviderRegistry = provider_registry_stub.InMemoryProviderRegistry
except ImportError:
    # If stub is not available, raise informative error
    raise ImportError(
        "bioetl.domain.provider_registry module was removed. "
        "For tests, ensure tests.fixtures.provider_registry_stub is available. "
        "The stub is automatically patched via pytest_configure in tests/conftest.py"
    )

__all__ = [
    "ProviderRegistryError",
    "ProviderNotRegisteredError",
    "ProviderAlreadyRegisteredError",
    "ProviderRegistryABC",
    "ProviderRegistryLoaderABC",
    "InMemoryProviderRegistry",
]

