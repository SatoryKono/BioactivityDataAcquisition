"""Provider registry domain abstractions (stub - module was removed)."""

# This module was removed. Import stub from tests when available.
# The stub is automatically patched via pytest_configure in tests/conftest.py

try:
    from tests.fixtures import provider_registry_stub

    # Re-export all symbols from stub
    stub = provider_registry_stub

    ProviderRegistryError = stub.ProviderRegistryError
    ProviderNotRegisteredError = stub.ProviderNotRegisteredError
    ProviderAlreadyRegisteredError = stub.ProviderAlreadyRegisteredError
    ProviderRegistryABC = stub.ProviderRegistryABC
    ProviderRegistryLoaderABC = stub.ProviderRegistryLoaderABC
    InMemoryProviderRegistry = stub.InMemoryProviderRegistry
except ImportError as exc:
    # If stub is not available, raise informative error
    raise ImportError(
        "bioetl.domain.provider_registry module was removed. "
        "For tests, ensure tests.fixtures.provider_registry_stub "
        "is available. "
        "The stub is automatically patched via pytest_configure in "
        "tests/conftest.py"
    ) from exc

__all__ = [
    "ProviderRegistryError",
    "ProviderNotRegisteredError",
    "ProviderAlreadyRegisteredError",
    "ProviderRegistryABC",
    "ProviderRegistryLoaderABC",
    "InMemoryProviderRegistry"
]
