"""Тесты для ApplicationBootstrap с моками инфраструктуры."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from bioetl.application.bootstrap import ApplicationBootstrap, create_application_bootstrap
from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.validation import SchemaProviderABC

if TYPE_CHECKING:  # pragma: no cover
    from bioetl.application.services.schema_bootstrap import SchemaBootstrapService

pytestmark = pytest.mark.unit


def _make_schema_bootstrap_service(schema_provider: SchemaProviderABC) -> SchemaBootstrapService:
    service = MagicMock()
    service.ensure_registered.return_value = schema_provider
    return service  # type: ignore[return-value]


class TestApplicationBootstrap:
    """Проверка базовой логики ApplicationBootstrap."""

    def test_start_uses_schema_bootstrap_service(self, monkeypatch: pytest.MonkeyPatch) -> None:
        schema_provider = MagicMock(spec=SchemaProviderABC)
        schema_service = _make_schema_bootstrap_service(schema_provider)

        monkeypatch.setattr(
            "bioetl.application.bootstrap.create_schema_bootstrap_service",
            lambda register_fn=None: schema_service,
        )

        bootstrap = ApplicationBootstrap()
        context = bootstrap.start()

        assert context.schema_provider is schema_provider
        schema_service.ensure_registered.assert_called_once()

    def test_start_is_idempotent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        schema_provider = MagicMock(spec=SchemaProviderABC)
        schema_service = _make_schema_bootstrap_service(schema_provider)
        monkeypatch.setattr(
            "bioetl.application.bootstrap.create_schema_bootstrap_service",
            lambda register_fn=None: schema_service,
        )

        bootstrap = ApplicationBootstrap()

        context1 = bootstrap.start()
        context2 = bootstrap.start()

        assert context1 is context2

    def test_config_loader_factory_receives_contract_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        schema_provider = MagicMock(spec=SchemaProviderABC)
        schema_service = _make_schema_bootstrap_service(schema_provider)
        monkeypatch.setattr(
            "bioetl.application.bootstrap.create_schema_bootstrap_service",
            lambda register_fn=None: schema_service,
        )

        captured: list[SchemaContractProviderABC] = []

        def mock_factory(provider: SchemaContractProviderABC) -> PipelineConfigLoaderProtocol:
            captured.append(provider)
            return MagicMock(spec=PipelineConfigLoaderProtocol)

        bootstrap = ApplicationBootstrap(config_loader_factory=mock_factory)
        context = bootstrap.start()

        assert captured == [context.contract_provider]
        assert context.config_loader is not None

    def test_provider_callbacks_invoked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        schema_provider = MagicMock(spec=SchemaProviderABC)
        schema_service = _make_schema_bootstrap_service(schema_provider)
        monkeypatch.setattr(
            "bioetl.application.bootstrap.create_schema_bootstrap_service",
            lambda register_fn=None: schema_service,
        )

        injected: list[SchemaContractProviderABC] = []
        cleared: list[bool] = []

        bootstrap = ApplicationBootstrap(
            provider_injector=lambda provider: injected.append(provider),
            provider_clearer=lambda: cleared.append(True),
        )

        context = bootstrap.start()
        bootstrap.shutdown()

        assert injected == [context.contract_provider]
        assert cleared == [True]

    def test_migration_service_factory_is_used(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        schema_provider = MagicMock(spec=SchemaProviderABC)
        schema_service = _make_schema_bootstrap_service(schema_provider)
        monkeypatch.setattr(
            "bioetl.application.bootstrap.create_schema_bootstrap_service",
            lambda register_fn=None: schema_service,
        )

        migration_service = MagicMock()
        bootstrap = ApplicationBootstrap(
            migration_service_factory=lambda: migration_service,
        )

        context = bootstrap.start()
        assert context.migration_service is migration_service

    def test_shutdown_resets_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        schema_provider = MagicMock(spec=SchemaProviderABC)
        schema_service = _make_schema_bootstrap_service(schema_provider)
        monkeypatch.setattr(
            "bioetl.application.bootstrap.create_schema_bootstrap_service",
            lambda register_fn=None: schema_service,
        )

        bootstrap = ApplicationBootstrap()
        bootstrap.start()
        bootstrap.shutdown()

        assert bootstrap.context is None
        assert not bootstrap.is_started


class TestCreateApplicationBootstrap:
    """Проверка фабричной функции create_application_bootstrap."""

    def test_returns_bootstrap_instance(self) -> None:
        bootstrap = create_application_bootstrap()

        assert isinstance(bootstrap, ApplicationBootstrap)

    def test_passes_factories_and_callbacks(self) -> None:
        def mock_factory(provider: SchemaContractProviderABC) -> PipelineConfigLoaderProtocol:
            return MagicMock(spec=PipelineConfigLoaderProtocol)

        def mock_injector(provider: SchemaContractProviderABC) -> None:
            provider  # pragma: no cover - side-effect free

        bootstrap = create_application_bootstrap(
            config_loader_factory=mock_factory,
            provider_injector=mock_injector,
        )

        assert isinstance(bootstrap, ApplicationBootstrap)
