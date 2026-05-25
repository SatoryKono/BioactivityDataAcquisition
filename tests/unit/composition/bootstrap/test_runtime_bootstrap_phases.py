"""Unit tests for runtime bootstrap phase helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from bioetl.composition.bootstrap.runtime import pipeline_bootstrap_phases as phases


def test_prepare_runtime_registry_creates_and_populates_registry() -> None:
    """Bootstrap registry prep should create, populate, and validate the registry."""
    registry = MagicMock()
    registry.list_pipelines.return_value = []

    with (
        patch.object(phases, "create_registry", return_value=registry) as mock_create,
        patch.object(phases, "ensure_providers_loaded") as mock_providers,
        patch.object(phases, "register_all_pipelines") as mock_register,
    ):
        result = phases.prepare_runtime_registry(
            registry=None,
            pipeline_name="chembl_activity",
        )

    assert result is registry
    mock_create.assert_called_once_with()
    mock_providers.assert_called_once_with()
    mock_register.assert_called_once_with(registry=registry)
    registry.get.assert_called_once_with("chembl_activity")


def test_prepare_runtime_registry_reuses_prepopulated_registry() -> None:
    """Bootstrap registry prep should not re-register populated registries."""
    registry = MagicMock()
    registry.list_pipelines.return_value = ["chembl_activity"]

    with (
        patch.object(phases, "create_registry") as mock_create,
        patch.object(phases, "ensure_providers_loaded") as mock_providers,
        patch.object(phases, "register_all_pipelines") as mock_register,
    ):
        result = phases.prepare_runtime_registry(
            registry=registry,
            pipeline_name="chembl_activity",
        )

    assert result is registry
    mock_create.assert_not_called()
    mock_providers.assert_called_once_with()
    mock_register.assert_not_called()
    registry.get.assert_called_once_with("chembl_activity")


def test_initialize_runtime_policy_sources_bootstraps_all_registries() -> None:
    """Runtime policy bootstrap should initialize every configured policy source."""
    configs_root = Path("/tmp/configs")

    with (
        patch.object(phases, "initialize_chembl_policy_registry") as mock_chembl,
        patch.object(
            phases,
            "initialize_publication_type_classification",
        ) as mock_classification,
        patch.object(
            phases,
            "initialize_publication_controlled_vocabulary",
        ) as mock_vocab,
    ):
        phases.initialize_runtime_policy_sources(configs_root)

    mock_chembl.assert_called_once_with(configs_root)
    mock_classification.assert_called_once_with(configs_root)
    mock_vocab.assert_called_once_with(configs_root)


def test_build_bootstrap_runner_factory_wiring_returns_noop_registry_wiring() -> None:
    """Factory wiring should become a no-op once bootstrap already populated registry."""
    wiring = phases.build_bootstrap_runner_factory_wiring()

    assert wiring.ensure_providers_loaded() is None
    assert wiring.register_all_pipelines(registry="ignored") is None


def test_build_bootstrap_runner_input_wiring_uses_lazy_bootstrap_seams() -> None:
    """Bootstrap input wiring should resolve canonical lazy config/observability seams."""
    configs_root = Path("/tmp/configs")
    pipeline_config_loader = MagicMock(name="load_pipeline_config")
    source_config_loader = MagicMock(name="load_source_config")

    with patch.object(
        phases,
        "create_source_config_loader",
        return_value=source_config_loader,
    ):
        wiring = phases.build_bootstrap_runner_input_wiring(
            configs_root=configs_root,
            load_pipeline_config_fn=pipeline_config_loader,
        )

    assert wiring.get_settings is phases.get_settings
    assert wiring.load_pipeline_config is pipeline_config_loader
    assert wiring.load_source_config is source_config_loader
    assert wiring.build_observability_bundle is phases.bootstrap_observability_bundle
    assert wiring.assemble_filter_config is phases.assemble_filter_config


def test_build_bootstrap_runner_input_wiring_builds_default_pipeline_loader() -> None:
    """Bootstrap input wiring should create a pipeline loader when one is not supplied."""
    configs_root = Path("/tmp/configs")
    pipeline_config_loader = MagicMock(name="load_pipeline_config")

    with (
        patch.object(
            phases,
            "create_pipeline_config_loader",
            return_value=pipeline_config_loader,
        ) as mock_create_pipeline_loader,
        patch.object(phases, "create_source_config_loader", return_value=MagicMock()),
    ):
        wiring = phases.build_bootstrap_runner_input_wiring(
            configs_root=configs_root,
            load_pipeline_config_fn=None,
        )

    mock_create_pipeline_loader.assert_called_once_with(configs_root)
    assert wiring.load_pipeline_config is pipeline_config_loader
