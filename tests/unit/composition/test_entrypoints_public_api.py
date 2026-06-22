"""Public API budget tests for ``bioetl.composition.entrypoints``."""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace
from unittest.mock import patch

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
    }

    assert set(entrypoints.__all__) == expected
    assert len(entrypoints.__all__) <= 15


@pytest.mark.unit
def test_entrypoints_retains_start_metrics_server_only_as_compatibility_wrapper() -> (
    None
):
    """Metrics startup stays callable but drops out of the official export budget."""
    entrypoints = _reload_entrypoints_module()

    assert "start_metrics_server" not in entrypoints.__all__
    assert callable(entrypoints.start_metrics_server)


@pytest.mark.unit
@pytest.mark.parametrize(
    "removed_name",
    (
        "get_checkpoint_service",
        "preview_cleanup",
    ),
)
def test_entrypoints_legacy_service_and_resource_symbols_are_removed(
    removed_name: str,
) -> None:
    """Legacy service/resource entrypoint shims should fail fast."""
    entrypoints = _reload_entrypoints_module()

    assert removed_name not in entrypoints.__all__
    assert removed_name not in dir(entrypoints)
    with pytest.raises(AttributeError):
        getattr(entrypoints, removed_name)


@pytest.mark.unit
@pytest.mark.parametrize(
    "removed_name",
    (
        "get_checkpoint_manager",
        "get_quarantine_manager",
    ),
)
def test_entrypoints_manager_aliases_are_removed_from_compatibility_surface(
    removed_name: str,
) -> None:
    """Manager-style entrypoint aliases should not survive as official shims."""
    entrypoints = _reload_entrypoints_module()

    assert removed_name not in dir(entrypoints)
    with pytest.raises(AttributeError):
        getattr(entrypoints, removed_name)


@pytest.mark.unit
def test_entrypoints_unknown_symbol_raises_attribute_error() -> None:
    """Unknown symbols should fail fast."""
    entrypoints = _reload_entrypoints_module()
    with pytest.raises(AttributeError):
        _ = entrypoints.not_existing_symbol


@pytest.mark.unit
def test_entrypoints_public_symbol_resolves_from_canonical_owner_module() -> None:
    """Lazy public exports should delegate to the documented owner module."""
    entrypoints = _reload_entrypoints_module()
    sentinel = object()

    def fake_import_module(module_name: str) -> SimpleNamespace:
        assert module_name == "bioetl.composition.execution_api"
        return SimpleNamespace(run_pipeline=sentinel)

    with patch(
        "bioetl.composition.lazy_exports.import_module",
        side_effect=fake_import_module,
    ) as import_module:
        assert entrypoints.run_pipeline is sentinel

    import_module.assert_called_once_with("bioetl.composition.execution_api")


@pytest.mark.unit
def test_resource_management_api_module_is_removed() -> None:
    """Legacy resource_management_api facade should no longer import."""
    sys.modules.pop("bioetl.composition.resource_management_api", None)

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("bioetl.composition.resource_management_api")


@pytest.mark.unit
def test_composition_package_root_surface_stays_frozen() -> None:
    """Package root should stay empty after lazy-export retirement."""
    composition_module = importlib.import_module("bioetl.composition")

    assert composition_module.__all__ == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "removed_name",
    (
        "create_registry",
        "get_default_registry",
        "PipelineRegistry",
        "PipelineDefinition",
        "types",
    ),
)
def test_composition_package_root_removed_lazy_exports_fail_fast(
    removed_name: str,
) -> None:
    """Removed package-root lazy exports should no longer resolve implicitly."""
    composition_module = importlib.import_module("bioetl.composition")

    assert removed_name not in composition_module.__all__
    with pytest.raises(AttributeError):
        getattr(composition_module, removed_name)


@pytest.mark.unit
def test_composition_package_root_budget_excludes_legacy_facade_modules() -> None:
    """Package-root export budget should not regrow legacy compatibility modules."""
    composition_module = importlib.import_module("bioetl.composition")

    assert "bootstrap" not in composition_module.__all__
    assert "resource_management_api" not in composition_module.__all__
    assert "services_api" not in composition_module.__all__


@pytest.mark.unit
def test_canonical_composition_owner_modules_remain_directly_importable() -> None:
    """Owner-focused composition APIs stay importable without package-root re-exports."""
    resources_api_module = importlib.import_module("bioetl.composition.resources_api")
    registry_api_module = importlib.import_module("bioetl.composition.registry_api")
    control_plane_api_module = importlib.import_module(
        "bioetl.composition.control_plane_api"
    )
    health_api_module = importlib.import_module("bioetl.composition.health_api")
    maintenance_api_module = importlib.import_module(
        "bioetl.composition.maintenance_api"
    )

    assert resources_api_module is not None
    assert registry_api_module is not None
    assert control_plane_api_module is not None
    assert health_api_module is not None
    assert maintenance_api_module is not None


@pytest.mark.unit
@pytest.mark.parametrize(
    "module_name",
    (
        "bioetl.composition.entrypoints",
        "bioetl.composition.health_api",
        "bioetl.composition.maintenance_api",
    ),
)
def test_public_composition_facades_do_not_duplicate_explicit_exports(
    module_name: str,
) -> None:
    """Explicit composition facade exports must stay unique and introspection-safe."""
    module = importlib.import_module(module_name)

    assert len(module.__all__) == len(set(module.__all__))
    assert set(module.__all__) <= set(dir(module))
