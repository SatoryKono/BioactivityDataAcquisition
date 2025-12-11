"""Tests for ApplicationBootstrap."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from bioetl.application.bootstrap import (
    ApplicationBootstrap,
    ApplicationContext,
    create_application_bootstrap,
)
from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.domain.validation import SchemaProviderABC

if TYPE_CHECKING:
    pass


class TestApplicationBootstrap:
    """Tests for ApplicationBootstrap class."""

    def test_start_returns_context(self) -> None:
        """Test that start() returns an ApplicationContext."""
        bootstrap = ApplicationBootstrap()
        context = bootstrap.start()

        assert isinstance(context, ApplicationContext)
        assert isinstance(context.schema_provider, SchemaProviderABC)
        assert isinstance(context.contract_provider, SchemaContractProviderABC)

    def test_start_is_idempotent(self) -> None:
        """Test that multiple calls to start() return the same context."""
        bootstrap = ApplicationBootstrap()

        context1 = bootstrap.start()
        context2 = bootstrap.start()

        assert context1 is context2

    def test_is_started_property(self) -> None:
        """Test is_started property reflects bootstrap state."""
        bootstrap = ApplicationBootstrap()

        assert not bootstrap.is_started

        bootstrap.start()

        assert bootstrap.is_started

    def test_context_property(self) -> None:
        """Test context property returns None before start and context after."""
        bootstrap = ApplicationBootstrap()

        assert bootstrap.context is None

        context = bootstrap.start()

        assert bootstrap.context is context

    def test_shutdown_resets_state(self) -> None:
        """Test that shutdown() resets the bootstrap state."""
        bootstrap = ApplicationBootstrap()
        bootstrap.start()

        assert bootstrap.is_started

        bootstrap.shutdown()

        assert not bootstrap.is_started
        assert bootstrap.context is None

    def test_can_restart_after_shutdown(self) -> None:
        """Test that bootstrap can be restarted after shutdown."""
        bootstrap = ApplicationBootstrap()

        context1 = bootstrap.start()
        bootstrap.shutdown()
        context2 = bootstrap.start()

        assert context1 is not context2
        assert bootstrap.is_started

    def test_config_loader_is_none_without_factory(self) -> None:
        """Test that config_loader is None when no factory is provided."""
        bootstrap = ApplicationBootstrap()
        context = bootstrap.start()

        assert context.config_loader is None

    def test_config_loader_factory_is_called(self) -> None:
        """Test that config_loader_factory is called with contract_provider."""
        captured_provider = []

        def mock_factory(
            provider: SchemaContractProviderABC,
        ) -> PipelineConfigLoaderProtocol:
            captured_provider.append(provider)
            return object()  # type: ignore

        bootstrap = ApplicationBootstrap(config_loader_factory=mock_factory)
        context = bootstrap.start()

        assert len(captured_provider) == 1
        assert captured_provider[0] is context.contract_provider
        assert context.config_loader is not None

    def test_provider_injector_is_called(self) -> None:
        """Test that provider_injector callback is called during start."""
        injected_providers = []

        def mock_injector(provider: SchemaContractProviderABC) -> None:
            injected_providers.append(provider)

        bootstrap = ApplicationBootstrap(provider_injector=mock_injector)
        context = bootstrap.start()

        assert len(injected_providers) == 1
        assert injected_providers[0] is context.contract_provider

    def test_provider_clearer_is_called_on_shutdown(self) -> None:
        """Test that provider_clearer callback is called during shutdown."""
        clear_called = []

        def mock_clearer() -> None:
            clear_called.append(True)

        bootstrap = ApplicationBootstrap(provider_clearer=mock_clearer)
        bootstrap.start()
        bootstrap.shutdown()

        assert len(clear_called) == 1


class TestCreateApplicationBootstrap:
    """Tests for create_application_bootstrap factory function."""

    def test_returns_bootstrap_instance(self) -> None:
        """Test that factory returns ApplicationBootstrap instance."""
        bootstrap = create_application_bootstrap()

        assert isinstance(bootstrap, ApplicationBootstrap)

    def test_accepts_config_loader_factory(self) -> None:
        """Test that factory accepts config_loader_factory parameter."""

        def mock_factory(
            provider: SchemaContractProviderABC,
        ) -> PipelineConfigLoaderProtocol:
            return object()  # type: ignore

        bootstrap = create_application_bootstrap(config_loader_factory=mock_factory)
        context = bootstrap.start()

        assert context.config_loader is not None

    def test_accepts_provider_callbacks(self) -> None:
        """Test that factory accepts provider callback parameters."""
        injected = []
        cleared = []

        bootstrap = create_application_bootstrap(
            provider_injector=lambda p: injected.append(p),
            provider_clearer=lambda: cleared.append(True),
        )

        bootstrap.start()
        assert len(injected) == 1

        bootstrap.shutdown()
        assert len(cleared) == 1


class TestApplicationContext:
    """Tests for ApplicationContext dataclass."""

    def test_is_frozen(self) -> None:
        """Test that ApplicationContext is immutable."""
        bootstrap = ApplicationBootstrap()
        context = bootstrap.start()

        with pytest.raises(Exception):  # FrozenInstanceError
            context.schema_provider = None  # type: ignore

    def test_has_required_attributes(self) -> None:
        """Test that context has all required attributes."""
        bootstrap = ApplicationBootstrap()
        context = bootstrap.start()

        assert hasattr(context, "schema_provider")
        assert hasattr(context, "contract_provider")
        assert hasattr(context, "config_loader")
