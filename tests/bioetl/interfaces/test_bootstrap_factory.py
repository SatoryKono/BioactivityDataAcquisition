from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.bootstrap import ApplicationBootstrap
from bioetl.interfaces import bootstrap_factory

pytestmark = pytest.mark.unit


class _BootstrapSpy(ApplicationBootstrap):
    def __init__(self, *, config_loader_factory, schema_register_fn):  # type: ignore[override]
        self.config_loader_factory = config_loader_factory
        self.schema_register_fn = schema_register_fn


class TestCreateDefaultBootstrap:
    """Юнит-тесты фабрики create_default_bootstrap с моками инфраструктуры."""

    def test_returns_bootstrap_instance(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "bioetl.domain.schemas.pipeline_contracts.set_contract_loader",
            lambda loader: loader,
        )
        monkeypatch.setattr(
            "bioetl.infrastructure.config.pipeline_contract_loader.get_default_contract_loader",
            lambda: object(),
        )
        monkeypatch.setattr(
            "bioetl.infrastructure.validation.bootstrap.register_schemas",
            MagicMock(),
        )
        monkeypatch.setattr(
            bootstrap_factory, "_create_config_loader_factory", lambda: MagicMock()
        )

        bootstrap = bootstrap_factory.create_default_bootstrap()

        assert isinstance(bootstrap, ApplicationBootstrap)

    def test_contract_loader_and_schema_registration_called(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        contract_loader = object()
        set_loader_calls: list[object] = []

        monkeypatch.setattr(
            "bioetl.infrastructure.config.pipeline_contract_loader.get_default_contract_loader",
            lambda: contract_loader,
        )
        monkeypatch.setattr(
            "bioetl.domain.schemas.pipeline_contracts.set_contract_loader",
            lambda loader: set_loader_calls.append(loader),
        )

        register_calls: list[object] = []
        monkeypatch.setattr(
            "bioetl.infrastructure.validation.bootstrap.register_schemas",
            lambda provider: register_calls.append(provider),
        )

        fake_config_factory = MagicMock()
        monkeypatch.setattr(
            bootstrap_factory, "_create_config_loader_factory", lambda: fake_config_factory
        )

        monkeypatch.setattr(bootstrap_factory, "ApplicationBootstrap", _BootstrapSpy)

        bootstrap = bootstrap_factory.create_default_bootstrap()

        assert isinstance(bootstrap, ApplicationBootstrap)
        assert set_loader_calls == [contract_loader]

        schema_provider = MagicMock()
        bootstrap.schema_register_fn(schema_provider)
        assert register_calls == [schema_provider]
        assert bootstrap.config_loader_factory is fake_config_factory
