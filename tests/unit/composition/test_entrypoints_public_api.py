# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Public API budget tests for ``bioetl.composition.entrypoints``."""

from __future__ import annotations

import importlib
import sys

import pytest


def _reload_entrypoints_module():
    sys.modules.pop("bioetl.composition.entrypoints", None)
    return importlib.import_module("bioetl.composition.entrypoints")


@pytest.mark.unit
def test_entrypoints_all_is_typed_registry_budget() -> None:
    """Explicit composition-root surface stays narrow and registry-focused."""
    entrypoints = _reload_entrypoints_module()

    expected = {
        "MedallionLifecycleServiceProtocol",
        "ensure_metrics_server_started",
        "get_contract_migration_service",
        "get_lifecycle_service",
        "get_pipeline_runner_service",
        "get_vacuum_service",
        "preview_cleanup",
        "register",
        "registered_ports",
        "resolve",
    }

    assert set(entrypoints.__all__) == expected
    assert len(entrypoints.__all__) <= 11


@pytest.mark.unit
@pytest.mark.parametrize("name", ["start_metrics_server", "load_pipeline_config"])
def test_entrypoints_removed_compatibility_wrappers_fail_fast(name: str) -> None:
    """Removed compatibility wrappers must not regrow on the typed registry."""
    entrypoints = _reload_entrypoints_module()

    assert name not in entrypoints.__all__
    with pytest.raises(AttributeError):
        getattr(entrypoints, name)


@pytest.mark.unit
def test_entrypoints_register_resolve_and_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The typed registry resolves factories and returns an isolated snapshot."""
    entrypoints = _reload_entrypoints_module()
    monkeypatch.setattr(entrypoints, "_REGISTRY", {})

    class Port:
        pass

    sentinel = object()
    entrypoints.register(Port, lambda: sentinel)

    assert entrypoints.resolve(Port) is sentinel
    snapshot = entrypoints.registered_ports()
    assert snapshot == {Port: snapshot[Port]}
    snapshot.clear()
    assert entrypoints.resolve(Port) is sentinel


@pytest.mark.unit
def test_entrypoints_resolve_unregistered_port_raises_key_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing registrations fail explicitly with the requested port in context."""
    entrypoints = _reload_entrypoints_module()
    monkeypatch.setattr(entrypoints, "_REGISTRY", {})

    class MissingPort:
        pass

    with pytest.raises(KeyError, match="no composition factory registered"):
        entrypoints.resolve(MissingPort)


@pytest.mark.unit
@pytest.mark.parametrize(
    "removed_name",
    (
        "get_checkpoint_service",
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
def test_entrypoints_public_symbol_is_owned_by_canonical_module() -> None:
    """Eager public exports should retain their documented implementation owner."""
    entrypoints = _reload_entrypoints_module()
    owner_module = entrypoints.ensure_metrics_server_started.__module__

    assert owner_module.endswith("pipeline_execution")
    assert owner_module.split(".")[-1].startswith("_")


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
    resources_api_module = importlib.import_module("bioetl.composition.resources_runtime")
    registry_api_module = importlib.import_module("bioetl.composition.registry_api")
    control_plane_api_module = importlib.import_module(
        "bioetl.composition.control_plane_runtime"
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
