from __future__ import annotations

from bioetl.domain.provider_registry import InMemoryProviderRegistry
from bioetl.domain.providers import ProviderId
from bioetl.infrastructure.clients.provider_registry_loader import (
    create_provider_loader,
)


def test_register_providers_registers_chembl() -> None:
    registry = InMemoryProviderRegistry()
    loader = create_provider_loader()
    loader.load_registry(registry=registry)

    provider = registry.get_provider(ProviderId.CHEMBL)
    assert provider.id == ProviderId.CHEMBL
    assert ProviderId.CHEMBL in {
        definition.id for definition in registry.list_providers()
    }


def test_register_providers_is_idempotent() -> None:
    registry = InMemoryProviderRegistry()
    loader = create_provider_loader()

    loader.load_registry(registry=registry)
    first_definition = registry.get_provider(ProviderId.CHEMBL)

    loader.load_registry(registry=registry)
    second_definition = registry.get_provider(ProviderId.CHEMBL)

    assert first_definition is second_definition
