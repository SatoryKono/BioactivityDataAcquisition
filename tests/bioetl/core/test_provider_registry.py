from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from bioetl.domain.provider_registry import (
    ProviderAlreadyRegisteredError,
    ProviderNotRegisteredError,
    get_provider,
    list_providers,
    register_provider,
    reset_provider_registry,
    restore_provider_registry,
)
from bioetl.domain.providers import (
    BaseProviderConfig,
    ProviderComponents,
    ProviderDefinition,
    ProviderId,
)


class DummyConfig(BaseProviderConfig):
    value: str = "payload"


@dataclass(frozen=True)
class DummyComponents(ProviderComponents[DummyConfig, str, str]):
    def create_client(self, config: DummyConfig) -> str:
        return f"client:{config.value}"

    def create_extraction_service(self, client: str, config: DummyConfig) -> str:
        return f"service:{client}:{config.value}"


@pytest.fixture(autouse=True)
def _reset_registry() -> Any:
    snapshot = list_providers()
    yield
    restore_provider_registry(snapshot)


def test_register_and_get_provider() -> None:
    reset_provider_registry()
    definition = ProviderDefinition(
        id=ProviderId.PUBCHEM,
        config_type=DummyConfig,
        components=DummyComponents(),
        description="PubChem provider for tests",
    )

    register_provider(definition)

    assert get_provider(ProviderId.PUBCHEM) == definition
    assert list_providers() == [definition]


def test_unknown_provider_raises() -> None:
    reset_provider_registry()

    with pytest.raises(ProviderNotRegisteredError):
        get_provider(ProviderId.CHEMBL)


def test_duplicate_registration_is_rejected() -> None:
    reset_provider_registry()
    definition = ProviderDefinition(
        id=ProviderId.UNIPROT,
        config_type=DummyConfig,
        components=DummyComponents(),
    )
    register_provider(definition)

    with pytest.raises(ProviderAlreadyRegisteredError):
        register_provider(definition)
