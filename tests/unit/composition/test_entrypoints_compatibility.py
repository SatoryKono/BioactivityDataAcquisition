"""Compatibility and API-budget tests for ``bioetl.composition.entrypoints``."""

from __future__ import annotations

import importlib
import sys

import pytest


def _reload_entrypoints_module():
    sys.modules.pop("bioetl.composition.entrypoints", None)
    return importlib.import_module("bioetl.composition.entrypoints")


@pytest.mark.unit
def test_entrypoints_all_is_execution_focused_budget() -> None:
    """Explicit public entrypoint surface should stay narrow and execution-focused."""
    entrypoints = _reload_entrypoints_module()

    expected = {
        "ArchiveOptions",
        "PipelineRunResult",
        "RunOptions",
        "RunResult",
        "VacuumOptions",
        "bootstrap_composite_runner",
        "build_pipeline_context",
        "create_pipeline_runner",
        "ensure_metrics_server_started",
        "load_composite_config",
        "load_pipeline_config",
        "maybe_start_metrics_server",
        "push_metrics_to_gateway",
        "run_pipeline",
        "start_metrics_server",
    }

    assert set(entrypoints.__all__) == expected
    assert len(entrypoints.__all__) <= 16


@pytest.mark.unit
def test_entrypoints_legacy_symbol_budget_stays_frozen() -> None:
    """Legacy compatibility lookup surface should stay intentionally bounded."""
    entrypoints = _reload_entrypoints_module()

    assert len(entrypoints._LEGACY_SYMBOL_TARGETS) == 24
    assert set(entrypoints._LEGACY_SYMBOL_TARGETS.values()) == {
        "bioetl.composition.resources_api",
        "bioetl.composition.services_api",
    }


@pytest.mark.unit
def test_entrypoints_legacy_service_symbol_warns_and_delegates() -> None:
    """Legacy service symbol should resolve via services_api with deprecation warning."""
    entrypoints = _reload_entrypoints_module()
    from bioetl.composition import services_api

    assert "get_checkpoint_service" not in entrypoints.__all__

    with pytest.deprecated_call(
        match=r"entrypoints\.get_checkpoint_service.*services_api"
    ):
        resolved = entrypoints.get_checkpoint_service

    assert resolved is services_api.get_checkpoint_service


@pytest.mark.unit
def test_entrypoints_legacy_resource_symbol_warns_and_delegates() -> None:
    """Legacy resource symbol should resolve via resources_api with warning."""
    entrypoints = _reload_entrypoints_module()
    from bioetl.composition import resources_api

    assert "preview_cleanup" not in entrypoints.__all__

    with pytest.deprecated_call(match=r"entrypoints\.preview_cleanup.*resources_api"):
        resolved = entrypoints.preview_cleanup

    assert resolved is resources_api.preview_cleanup


@pytest.mark.unit
def test_entrypoints_unknown_symbol_raises_attribute_error() -> None:
    """Unknown symbols should fail fast."""
    entrypoints = _reload_entrypoints_module()
    with pytest.raises(AttributeError):
        _ = entrypoints.not_existing_symbol


@pytest.mark.unit
def test_resource_management_api_alias_warns_and_reexports_resources_api() -> None:
    """Deprecated module alias should warn and forward to resources_api symbols."""
    sys.modules.pop("bioetl.composition.resource_management_api", None)

    with pytest.deprecated_call(match=r"resource_management_api.*resources_api"):
        alias_module = importlib.import_module(
            "bioetl.composition.resource_management_api"
        )

    from bioetl.composition import resources_api

    assert alias_module.__all__ == resources_api.__all__
    assert (
        alias_module.get_checkpoint_runtime_service
        is resources_api.get_checkpoint_runtime_service
    )


@pytest.mark.unit
def test_composition_package_root_surface_stays_frozen() -> None:
    """Package root should keep the reviewed lazy-export budget exactly bounded."""
    composition_module = importlib.import_module("bioetl.composition")

    assert set(composition_module.__all__) == {
        "PipelineDefinition",
        "PipelineRegistry",
        "composite_api",
        "control_plane_api",
        "create_registry",
        "entrypoints",
        "execution_api",
        "get_default_registry",
        "health_api",
        "maintenance_api",
        "observability_api",
        "registry_api",
        "resources_api",
        "types",
    }
    assert len(composition_module.__all__) <= 14


@pytest.mark.unit
def test_composition_package_root_exports_resources_api_module() -> None:
    """Package root should expose canonical resources_api lazy export."""
    composition_module = importlib.import_module("bioetl.composition")
    resources_api_module = importlib.import_module("bioetl.composition.resources_api")

    assert "resources_api" in composition_module.__all__
    assert composition_module.resources_api is resources_api_module


@pytest.mark.unit
def test_composition_package_root_budget_excludes_legacy_facade_modules() -> None:
    """Package-root export budget should not regrow legacy compatibility modules."""
    composition_module = importlib.import_module("bioetl.composition")

    assert "bootstrap" not in composition_module.__all__
    assert "resource_management_api" not in composition_module.__all__
    assert "services_api" not in composition_module.__all__


@pytest.mark.unit
def test_composition_package_root_exports_registry_api_module() -> None:
    """Package root should expose canonical registry_api lazy export."""
    composition_module = importlib.import_module("bioetl.composition")
    registry_api_module = importlib.import_module("bioetl.composition.registry_api")

    assert "registry_api" in composition_module.__all__
    assert composition_module.registry_api is registry_api_module


@pytest.mark.unit
def test_composition_package_root_exports_narrow_service_api_modules() -> None:
    """Package root should expose the sanctioned narrow service API modules."""
    composition_module = importlib.import_module("bioetl.composition")
    control_plane_api_module = importlib.import_module(
        "bioetl.composition.control_plane_api"
    )
    health_api_module = importlib.import_module("bioetl.composition.health_api")
    maintenance_api_module = importlib.import_module(
        "bioetl.composition.maintenance_api"
    )

    assert "control_plane_api" in composition_module.__all__
    assert "health_api" in composition_module.__all__
    assert "maintenance_api" in composition_module.__all__
    assert composition_module.control_plane_api is control_plane_api_module
    assert composition_module.health_api is health_api_module
    assert composition_module.maintenance_api is maintenance_api_module
