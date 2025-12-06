from __future__ import annotations

from dataclasses import dataclass

import pytest

from bioetl.domain.provider_registry import (
    InMemoryProviderRegistry,
    ProviderAlreadyRegisteredError,
    ProviderNotRegisteredError,
)
from bioetl.domain.providers import ProviderComponents, ProviderDefinition, ProviderId
from bioetl.infrastructure.config.models import DummyProviderConfig


@dataclass(frozen=True)
class DummyComponents(ProviderComponents):
    def create_client(self, config: DummyProviderConfig) -> dict[str, str]:
        return {"base_url": str(config.base_url)}

    def create_extraction_service(
        self,
        config: DummyProviderConfig,
        *,
        client: dict[str, str] | None = None,
    ) -> tuple[dict[str, str], str]:
        resolved_client = client or self.create_client(config)
        return resolved_client, config.provider


@pytest.fixture
def registry() -> InMemoryProviderRegistry:
    return InMemoryProviderRegistry()


def test_register_and_get_provider(registry: InMemoryProviderRegistry) -> None:
    definition = ProviderDefinition(
        id=ProviderId.DUMMY,
        config_type=DummyProviderConfig,
        components=DummyComponents(),
        description="Dummy provider for tests",
    )

    registry.register_provider(definition)

    assert registry.get_provider(ProviderId.DUMMY) == definition
    assert registry.list_providers() == [definition]


def test_unknown_provider_raises(registry: InMemoryProviderRegistry) -> None:
    with pytest.raises(ProviderNotRegisteredError):
        registry.get_provider(ProviderId.CHEMBL)


def test_duplicate_registration_is_rejected(
    registry: InMemoryProviderRegistry,
) -> None:
    definition = ProviderDefinition(
        id=ProviderId.DUMMY,
        config_type=DummyProviderConfig,
        components=DummyComponents(),
    )
    registry.register_provider(definition)

    with pytest.raises(ProviderAlreadyRegisteredError):
        registry.register_provider(definition)
