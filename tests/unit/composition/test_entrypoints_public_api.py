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
        "maybe_start_metrics_server",
        "push_metrics_to_gateway",
        "run_pipeline",
    }

    assert set(entrypoints.__all__) == expected
    assert len(entrypoints.__all__) <= 14


@pytest.mark.unit
def test_entrypoints_retains_start_metrics_server_only_as_compatibility_wrapper() -> (
    None
):
    """Metrics startup stays callable but drops out of the official export budget."""
    entrypoints = _reload_entrypoints_module()

    assert "start_metrics_server" not in entrypoints.__all__
    assert callable(entrypoints.start_metrics_server)


@pytest.mark.unit
def test_entrypoints_start_metrics_server_wrapper_delegates_to_observability_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compatibility wrapper must forward kwargs to observability-owned startup."""
    entrypoints = _reload_entrypoints_module()
    calls: list[dict[str, object]] = []

    def _fake_start(
        port: int = 8000,
        addr: str = "0.0.0.0",
        *,
        fail_fast: bool = False,
        retry_count: int = 3,
        retry_delay: float = 1.0,
        logger: object | None = None,
    ) -> bool:
        calls.append(
            {
                "port": port,
                "addr": addr,
                "fail_fast": fail_fast,
                "retry_count": retry_count,
                "retry_delay": retry_delay,
                "logger": logger,
            }
        )
        return True

    monkeypatch.setattr(
        "bioetl.composition.observability_runtime.start_metrics_server",
        _fake_start,
    )
    logger = object()
    assert (
        entrypoints.start_metrics_server(
            9100,
            "127.0.0.1",
            fail_fast=True,
            retry_count=2,
            retry_delay=0.5,
            logger=logger,  # type: ignore[arg-type]
        )
        is True
    )
    assert calls == [
        {
            "port": 9100,
            "addr": "127.0.0.1",
            "fail_fast": True,
            "retry_count": 2,
            "retry_delay": 0.5,
            "logger": logger,
        }
    ]


@pytest.mark.unit
def test_entrypoints_retains_load_pipeline_config_only_as_compatibility_wrapper() -> (
    None
):
    """Pipeline config loading stays callable but drops out of the official export budget."""
    entrypoints = _reload_entrypoints_module()

    assert "load_pipeline_config" not in entrypoints.__all__
    assert callable(entrypoints.load_pipeline_config)


@pytest.mark.unit
def test_entrypoints_load_pipeline_config_wrapper_delegates_to_composite_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compatibility wrapper must forward pipeline names to composite-owned loader."""
    entrypoints = _reload_entrypoints_module()
    sentinel = object()
    seen: list[str] = []

    def _fake_load(pipeline_name: str) -> object:
        seen.append(pipeline_name)
        return sentinel

    monkeypatch.setattr(
        "bioetl.composition.composite_catalog.load_pipeline_config",
        _fake_load,
    )
    assert entrypoints.load_pipeline_config("chembl_activity") is sentinel
    assert seen == ["chembl_activity"]


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
