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
from bioetl.domain.providers import ProviderComponents, ProviderDefinition, ProviderId
from bioetl.infrastructure.config.models import DummyProviderConfig


@dataclass(frozen=True)
class DummyComponents(
    ProviderComponents[DummyProviderConfig, dict[str, str], tuple[dict[str, str], str]]
):
    def create_client(self, config: DummyProviderConfig) -> dict[str, str]:
        return {"base_url": str(config.base_url)}

    def create_extraction_service(
        self, client: dict[str, str], config: DummyProviderConfig
    ) -> tuple[dict[str, str], str]:
        return client, config.provider


@pytest.fixture(autouse=True)
def _reset_registry() -> Any:
    snapshot = list_providers()
    yield
    restore_provider_registry(snapshot)


def test_register_and_get_provider() -> None:
    reset_provider_registry()
    definition = ProviderDefinition(
        id=ProviderId.DUMMY,
        config_type=DummyProviderConfig,
        components=DummyComponents(),
        description="Dummy provider for tests",
    )

    register_provider(definition)

    assert get_provider(ProviderId.DUMMY) == definition
    assert list_providers() == [definition]


def test_unknown_provider_raises() -> None:
    reset_provider_registry()

    with pytest.raises(ProviderNotRegisteredError):
        get_provider(ProviderId.CHEMBL)


def test_duplicate_registration_is_rejected() -> None:
    reset_provider_registry()
    definition = ProviderDefinition(
        id=ProviderId.DUMMY,
        config_type=DummyProviderConfig,
        components=DummyComponents(),
    )
    register_provider(definition)

    with pytest.raises(ProviderAlreadyRegisteredError):
        register_provider(definition)
