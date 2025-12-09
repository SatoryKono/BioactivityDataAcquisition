from __future__ import annotations

from dataclasses import dataclass
import sys
from types import ModuleType
from typing import Any, Callable

import pytest

from bioetl.domain.configs import DummyProviderConfig

from bioetl.domain.provider_registry import InMemoryProviderRegistry
from bioetl.domain.providers import ProviderComponents, ProviderDefinition, ProviderId
from bioetl.interfaces.observability import LoggingPortABC


@dataclass(frozen=True)
class DummyComponents(ProviderComponents):
    def create_client(self, config: DummyProviderConfig) -> dict[str, str]:
        return {"provider": config.provider}

    def create_extraction_service(
        self, config: DummyProviderConfig, *, client: dict[str, str] | None = None
    ) -> tuple[dict[str, str], str]:
        resolved_client = client or self.create_client(config)
        return resolved_client, config.provider


class RecordingLogger(LoggingPortABC):
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

    def apply_bind(self, **ctx: Any) -> RecordingLogger:
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


# @pytest.mark.skip(reason="Provider registry module was removed")
def test_loader_handles_disabled_and_faulty_entries() -> None:
    """Legacy provider registry loader test disabled until module returns."""


# @pytest.mark.skip(reason="Provider registry module was removed")
def test_loader_reuses_existing_definition_on_duplicate_entries() -> None:
    """Legacy provider registry loader test disabled until module returns."""
