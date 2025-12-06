from __future__ import annotations

from bioetl.domain.provider_registry import InMemoryProviderRegistry
from bioetl.domain.providers import ProviderId
from bioetl.infrastructure.clients.provider_registry_loader import (
    load_provider_registry,
)


def test_register_providers_registers_chembl() -> None:
    registry = InMemoryProviderRegistry()
    load_provider_registry(registry=registry)

    provider = registry.get_provider(ProviderId.CHEMBL)
    assert provider.id == ProviderId.CHEMBL
    assert ProviderId.CHEMBL in {
        definition.id for definition in registry.list_providers()
    }


def test_register_providers_is_idempotent() -> None:
    registry = InMemoryProviderRegistry()

    load_provider_registry(registry=registry)
    first_definition = registry.get_provider(ProviderId.CHEMBL)

    load_provider_registry(registry=registry)
    second_definition = registry.get_provider(ProviderId.CHEMBL)

    assert first_definition is second_definition
