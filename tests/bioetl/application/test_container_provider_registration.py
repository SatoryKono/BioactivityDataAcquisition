from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.domain.providers import ProviderId
from bioetl.infrastructure.config.provider_registry import (
    create_provider_loader,
)
from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry

_TEST_PROVIDERS_CONFIG = Path("tests/fixtures/configs/providers.yaml")


def _create_loader():
    return create_provider_loader(config_path=_TEST_PROVIDERS_CONFIG)


def test_register_providers_registers_chembl() -> None:
    registry = InMemoryProviderRegistry()
    loader = _create_loader()
    loader.get_registry(registry=registry)

    provider = registry.get_provider(ProviderId.CHEMBL)
    assert provider.id == ProviderId.CHEMBL
    assert ProviderId.CHEMBL in {
        definition.id for definition in registry.list_providers()
    }


def test_register_providers_is_idempotent() -> None:
    pytest.skip("Provider registry module was removed")
