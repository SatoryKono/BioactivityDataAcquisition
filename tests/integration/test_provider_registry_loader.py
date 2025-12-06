from __future__ import annotations

import sys
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Callable

import pytest
import yaml

from bioetl.clients.base.logging.contracts import LoggerAdapterABC
from bioetl.domain.configs import DummyProviderConfig
from bioetl.domain.provider_registry import InMemoryProviderRegistry
from bioetl.domain.providers import ProviderComponents, ProviderDefinition, ProviderId
from bioetl.infrastructure.clients.provider_registry_loader import (
    ProviderRegistryLoader,
)


@dataclass(frozen=True)
class DummyComponents(ProviderComponents):
    def create_client(self, config: DummyProviderConfig) -> dict[str, str]:
        return {"provider": config.provider}

    def create_extraction_service(
        self, config: DummyProviderConfig, *, client: dict[str, str] | None = None
    ) -> tuple[dict[str, str], str]:
        resolved_client = client or self.create_client(config)
        return resolved_client, config.provider


class RecordingLogger(LoggerAdapterABC):
    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict[str, Any]]] = []

    def info(self, msg: str, **ctx: Any) -> None:
        self.records.append(("info", msg, ctx))

    def error(self, msg: str, **ctx: Any) -> None:
        self.records.append(("error", msg, ctx))

    def debug(self, msg: str, **ctx: Any) -> None:
        self.records.append(("debug", msg, ctx))

    def warning(self, msg: str, **ctx: Any) -> None:
        self.records.append(("warning", msg, ctx))

    def bind(self, **ctx: Any) -> RecordingLogger:
        self.records.append(("bind", "", ctx))
        return self

    @property
    def errors(self) -> list[tuple[str, str, dict[str, Any]]]:
        return [record for record in self.records if record[0] == "error"]

    @property
    def debugs(self) -> list[tuple[str, str, dict[str, Any]]]:
        return [record for record in self.records if record[0] == "debug"]


@pytest.fixture
def provider_definition_factory() -> Callable[[ProviderId], ProviderDefinition]:
    def _factory(provider_id: ProviderId) -> ProviderDefinition:
        return ProviderDefinition(
            id=provider_id,
            config_type=DummyProviderConfig,
            components=DummyComponents(),
            description="Test provider",
        )

    return _factory


def _register_module(
    module_name: str, factory_name: str, factory: Callable[[], Any]
) -> None:
    module = ModuleType(module_name)
    setattr(module, factory_name, factory)
    sys.modules[module_name] = module


def test_loader_handles_disabled_and_faulty_entries(
    tmp_path: Any,
    provider_definition_factory: Callable[[ProviderId], ProviderDefinition],
) -> None:
    valid_module = "tests.integration.providers.active"
    valid_factory_name = "build_provider"
    valid_definition = provider_definition_factory(ProviderId.DUMMY)
    _register_module(valid_module, valid_factory_name, lambda: valid_definition)

    broken_module = "tests.integration.providers.broken"
    broken_factory_name = "broken_factory"

    def _broken_factory() -> None:
        raise RuntimeError("boom")

    _register_module(broken_module, broken_factory_name, _broken_factory)

    config_path = tmp_path / "providers.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "providers": [
                    {
                        "id": ProviderId.DUMMY.value,
                        "module": valid_module,
                        "factory": valid_factory_name,
                        "active": True,
                    },
                    {
                        "id": ProviderId.DUMMY.value,
                        "module": valid_module,
                        "factory": valid_factory_name,
                        "active": False,
                    },
                    {
                        "id": ProviderId.PUBCHEM.value,
                        "module": "non.existent.module",
                        "factory": "missing_factory",
                        "active": True,
                    },
                    {
                        "id": ProviderId.UNIPROT.value,
                        "module": broken_module,
                        "factory": broken_factory_name,
                        "active": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    registry = InMemoryProviderRegistry()
    logger = RecordingLogger()
    loader = ProviderRegistryLoader(config_path=config_path, logger=logger)

    registered = loader.load(registry=registry)

    assert registered == [valid_definition]
    assert registry.list_providers() == [valid_definition]
    assert any(
        message == "Failed to import provider module" for _, message, _ in logger.errors
    )
    assert any(
        message == "Provider factory invocation failed"
        for _, message, _ in logger.errors
    )


def test_loader_reuses_existing_definition_on_duplicate_entries(
    tmp_path: Any,
    provider_definition_factory: Callable[[ProviderId], ProviderDefinition],
) -> None:
    duplicate_module = "tests.integration.providers.duplicate"
    factory_name = "build_provider"
    definition = provider_definition_factory(ProviderId.DUMMY)
    _register_module(duplicate_module, factory_name, lambda: definition)

    config_path = tmp_path / "providers.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "providers": [
                    {
                        "id": ProviderId.DUMMY.value,
                        "module": duplicate_module,
                        "factory": factory_name,
                        "active": True,
                    },
                    {
                        "id": ProviderId.DUMMY.value,
                        "module": duplicate_module,
                        "factory": factory_name,
                        "active": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    registry = InMemoryProviderRegistry()
    logger = RecordingLogger()
    loader = ProviderRegistryLoader(config_path=config_path, logger=logger)

    registered = loader.load(registry=registry)

    assert registered == [definition, definition]
    assert registry.list_providers() == [definition]
    assert any(
        message == "Provider already registered; reusing existing definition"
        for level, message, _ in logger.debugs
    )
