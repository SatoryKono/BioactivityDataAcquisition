"""Unit tests for runtime bootstrap phase helpers."""

from __future__ import annotations

import pytest

from pathlib import Path
from unittest.mock import MagicMock, patch

from bioetl.composition.bootstrap.runtime import pipeline_bootstrap_phases as phases


pytestmark = pytest.mark.unit


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
            "initialize_protein_class_target_type_mapping",
        ) as mock_protein_class_mapping,
        patch.object(
            phases,
            "initialize_publication_controlled_vocabulary",
        ) as mock_vocab,
    ):
        phases.initialize_runtime_policy_sources(configs_root)

    mock_chembl.assert_called_once_with(configs_root)
    mock_classification.assert_called_once_with(configs_root)
    mock_protein_class_mapping.assert_called_once_with(configs_root)
    mock_vocab.assert_called_once_with(configs_root)


def test_bootstrap_observability_bundle_executes_lazy_wrapper() -> None:
    """The lazy wrapper must not evaluate type-only imports at runtime."""
    expected_bundle = MagicMock()
    run_id = MagicMock()
    settings = MagicMock()

    with patch(
        "bioetl.composition.bootstrap.runtime.observability_bundle."
        "bootstrap_observability_bundle_impl",
        return_value=expected_bundle,
    ) as mock_bootstrap:
        result = phases.bootstrap_observability_bundle(
            pipeline="chembl_activity",
            run_id=run_id,
            settings=settings,
            log_level="INFO",
        )

    assert result is expected_bundle
    mock_bootstrap.assert_called_once_with(
        pipeline="chembl_activity",
        run_id=run_id,
        settings=settings,
        log_level="INFO",
        logger_bootstrapper=None,
        tracer_bootstrapper=None,
        metrics_bootstrapper=None,
        audit_bootstrapper=None,
        dq_monitor_bootstrapper=None,
        preflight_validator=None,
        yaml_config=None,
        skip_gold=False,
    )
