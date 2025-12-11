"""Tests for bootstrap_factory in interfaces layer."""

from __future__ import annotations

from bioetl.application.bootstrap import ApplicationBootstrap, ApplicationContext
from bioetl.interfaces.bootstrap_factory import create_default_bootstrap


class TestCreateDefaultBootstrap:
    """Tests for create_default_bootstrap factory function."""

    def test_returns_bootstrap_instance(self) -> None:
        """Test that factory returns ApplicationBootstrap instance."""
        bootstrap = create_default_bootstrap()

        assert isinstance(bootstrap, ApplicationBootstrap)

    def test_bootstrap_starts_successfully(self) -> None:
        """Test that created bootstrap starts without errors."""
        bootstrap = create_default_bootstrap()
        context = bootstrap.start()

        assert isinstance(context, ApplicationContext)

    def test_context_has_config_loader(self) -> None:
        """Test that context from default bootstrap has config_loader."""
        bootstrap = create_default_bootstrap()
        context = bootstrap.start()

        assert context.config_loader is not None

    def test_config_loader_has_get_by_id(self) -> None:
        """Test that config_loader has get_by_id method."""
        bootstrap = create_default_bootstrap()
        context = bootstrap.start()

        assert hasattr(context.config_loader, "get_by_id")
        assert callable(context.config_loader.get_by_id)

    def test_config_loader_has_get_from_path(self) -> None:
        """Test that config_loader has get_from_path method."""
        bootstrap = create_default_bootstrap()
        context = bootstrap.start()

        assert hasattr(context.config_loader, "get_from_path")
        assert callable(context.config_loader.get_from_path)

    def test_shutdown_clears_state(self) -> None:
        """Test that shutdown clears bootstrap state."""
        bootstrap = create_default_bootstrap()
        bootstrap.start()

        assert bootstrap.is_started

        bootstrap.shutdown()

        assert not bootstrap.is_started

    def test_multiple_bootstraps_are_independent(self) -> None:
        """Test that multiple bootstrap instances are independent."""
        bootstrap1 = create_default_bootstrap()
        bootstrap2 = create_default_bootstrap()

        context1 = bootstrap1.start()
        context2 = bootstrap2.start()

        # Contexts should be different objects
        assert context1 is not context2

        # But both should be valid
        assert context1.schema_provider is not None
        assert context2.schema_provider is not None
