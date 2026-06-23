"""Unit tests for CLI config bootstrap.

Tests bootstrap_config_service wires ConfigService with correct
infrastructure dependencies via DI.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.services.config_service import ConfigService
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.composition.bootstrap.cli.config import bootstrap_config_service
from bioetl.domain.config import DQConfig
from bioetl.infrastructure.observability.noop_logger import NoOpLogger


@pytest.mark.unit
class TestBootstrapConfigService:
    """Tests for bootstrap_config_service function."""

    @patch("bioetl.composition.bootstrap.cli.config.register_all_pipelines")
    def test_returns_config_service(
        self,
        mock_register: MagicMock,
    ) -> None:
        """bootstrap_config_service should return a ConfigService instance."""
        result = bootstrap_config_service()

        assert isinstance(result, ConfigService)

    @patch("bioetl.composition.bootstrap.cli.config.register_all_pipelines")
    def test_wires_noop_logger(
        self,
        mock_register: MagicMock,
    ) -> None:
        """bootstrap_config_service should wire a NoOpLogger."""
        result = bootstrap_config_service()

        assert isinstance(result.logger, NoOpLogger)

    @patch("bioetl.composition.bootstrap.cli.config.register_all_pipelines")
    def test_calls_register_all_pipelines(
        self,
        mock_register: MagicMock,
    ) -> None:
        """bootstrap_config_service should call register_all_pipelines for registry."""
        bootstrap_config_service()

        mock_register.assert_called_once()
        assert "registry" in mock_register.call_args.kwargs

    @patch("bioetl.composition.bootstrap.cli.config.register_all_pipelines")
    def test_each_call_creates_new_instance(
        self,
        mock_register: MagicMock,
    ) -> None:
        """Each call to bootstrap_config_service should create a new ConfigService."""
        result1 = bootstrap_config_service()
        result2 = bootstrap_config_service()

        assert result1 is not result2

    @patch("bioetl.composition.bootstrap.cli.config.register_all_pipelines")
    def test_wires_settings_loader(
        self,
        mock_register: MagicMock,
    ) -> None:
        """bootstrap_config_service should wire a settings loader callable."""
        result = bootstrap_config_service()

        # _settings_loader should be callable
        assert callable(result._settings_loader)

    @patch("bioetl.composition.bootstrap.cli.config.register_all_pipelines")
    def test_wires_pipeline_config_loader(
        self,
        mock_register: MagicMock,
    ) -> None:
        """bootstrap_config_service should wire a pipeline config loader."""
        result = bootstrap_config_service()

        assert callable(result._pipeline_config_loader)

    @patch("bioetl.composition.bootstrap.cli.config.register_all_pipelines")
    def test_wires_registry_accessor(
        self,
        mock_register: MagicMock,
    ) -> None:
        """bootstrap_config_service should wire a registry accessor callable."""
        result = bootstrap_config_service()

        assert callable(result._registry_accessor)

    @patch("bioetl.composition.bootstrap.cli.config.register_all_pipelines")
    def test_wires_domain_config_mapper(
        self,
        mock_register: MagicMock,
    ) -> None:
        """bootstrap_config_service should wire a domain config mapper."""
        result = bootstrap_config_service()

        assert callable(result._domain_config_mapper)

    @patch("bioetl.composition.bootstrap.cli.config.register_all_pipelines")
    def test_register_all_pipelines_called_before_service_creation(
        self,
        mock_register: MagicMock,
    ) -> None:
        """register_all_pipelines must be called before ConfigService is returned."""
        call_order: list[str] = []
        mock_register.side_effect = lambda *args, **kwargs: call_order.append(
            "register"
        )

        # Monkeypatch ConfigService to track call order
        original_init = ConfigService.__init__

        def patched_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            call_order.append("init")
            original_init(self, *args, **kwargs)

        ConfigService.__init__ = patched_init  # type: ignore[method-assign]
        try:
            bootstrap_config_service()
        finally:
            ConfigService.__init__ = original_init  # type: ignore[method-assign]

        # register must come before init
        assert call_order.index("register") < call_order.index("init")

    @patch("bioetl.composition.bootstrap.cli.config.register_all_pipelines")
    def test_registers_explicit_registry_in_composition_root(
        self,
        mock_register: MagicMock,
    ) -> None:
        """Explicit registry injection keeps registration in the composition root."""
        registry = PipelineRegistry()

        result = bootstrap_config_service(registry=registry)

        assert result._registry_accessor() is registry
        mock_register.assert_called_once_with(registry=registry)

    @patch("bioetl.composition.bootstrap.cli.config.create_dq_config_loader")
    @patch("bioetl.composition.bootstrap.cli.config.register_all_pipelines")
    def test_dq_loader_receives_explicit_configs_root(
        self,
        mock_register: MagicMock,
        mock_create_dq_loader: MagicMock,
    ) -> None:
        """DQ contract loader wiring must not depend on process CWD."""
        configs_root = Path("/tmp/bioetl-configs")
        bound_loader = MagicMock(name="dq_config_loader")
        bound_loader.return_value = DQConfig(contract_ref="chembl.activity")
        mock_create_dq_loader.return_value = bound_loader

        result = bootstrap_config_service(configs_root=configs_root)
        dq_config = result._dq_service._dq_config_loader("chembl_activity")

        assert dq_config.contract_ref == "chembl.activity"
        mock_create_dq_loader.assert_called_once_with(configs_root)
        bound_loader.assert_called_once_with("chembl_activity")

    @patch("bioetl.composition.bootstrap.cli.config.create_pipeline_config_loader")
    @patch("bioetl.composition.bootstrap.cli.config.resolve_configs_root")
    @patch("bioetl.composition.bootstrap.cli.config.register_all_pipelines")
    def test_resolves_configs_root_before_binding_pipeline_loader(
        self,
        mock_register: MagicMock,
        mock_resolve_configs_root: MagicMock,
        mock_create_pipeline_loader: MagicMock,
    ) -> None:
        """CLI config bootstrap should bind one explicit configs root."""
        requested_root = Path("relative-configs")
        resolved_root = Path("/tmp/bioetl-configs")
        mock_resolve_configs_root.return_value = resolved_root
        bound_loader = MagicMock(name="pipeline_config_loader")
        mock_create_pipeline_loader.return_value = bound_loader

        result = bootstrap_config_service(configs_root=requested_root)

        mock_resolve_configs_root.assert_called_once_with(requested_root)
        mock_create_pipeline_loader.assert_called_once_with(resolved_root)
        assert result._pipeline_config_loader is bound_loader
