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
"""Unit tests for retired application/core wiring API facades."""

from __future__ import annotations

import importlib

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "module_name",
    [
        "bioetl.application.core.pipeline_registry_wiring_api",
        "bioetl.application.core.runtime_wiring_api",
        "bioetl.application.core.transformer_wiring_api",
    ],
)
def test_legacy_wiring_api_facades_stay_removed(module_name: str) -> None:
    """Legacy flat wiring facades must not be reintroduced."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)


def test_canonical_wiring_owner_modules_remain_importable() -> None:
    """The split owner modules remain the supported first-party import paths."""
    from bioetl.application.core.wiring.factory import PipelineRunner
    from bioetl.application.core.wiring.registry import ActivityTransformer
    from bioetl.application.core.wiring.transformer import BaseTransformer

    assert isinstance(ActivityTransformer, type)
    assert isinstance(PipelineRunner, type)
    assert isinstance(BaseTransformer, type)


def test_canonical_wiring_package_lazy_exports_owner_symbols() -> None:
    """The package facade exposes owner modules without reintroducing flat APIs."""
    import bioetl.application.core.wiring as wiring

    assert isinstance(wiring.PipelineRunner, type)
    assert isinstance(wiring.ActivityTransformer, type)
    assert isinstance(wiring.TargetProteinClassificationTransformer, type)
    assert "PipelineRunner" in dir(wiring)
    assert "ActivityTransformer" in dir(wiring)
    assert "TargetProteinClassificationTransformer" in wiring.__all__

    missing_name = "does_not_exist"
    with pytest.raises(AttributeError, match=missing_name):
        getattr(wiring, missing_name)


def test_wiring_package_init_uses_static_export_map_without_submodule_import() -> None:
    """Importing the package must not eagerly import factory/registry/runtime/transformer."""
    import sys

    package_name = "bioetl.application.core.wiring"
    owner_prefixes = (
        "bioetl.application.core.wiring.factory",
        "bioetl.application.core.wiring.registry",
        "bioetl.application.core.wiring.runtime",
        "bioetl.application.core.wiring.transformer",
    )

    stale = [
        name
        for name in list(sys.modules)
        if name == package_name or name.startswith(package_name + ".")
    ]
    for name in stale:
        del sys.modules[name]

    wiring = importlib.import_module(package_name)

    for owner in owner_prefixes:
        assert owner not in sys.modules, f"eager import of {owner}"
    assert isinstance(wiring._EXPORT_MODULES, dict)
    assert "PipelineRunner" in wiring._EXPORT_MODULES
    assert wiring._EXPORT_MODULES["PipelineRunner"].endswith(".factory")
    # Shared names resolve to the last declared group (runtime overwrites factory).
    assert wiring._EXPORT_MODULES["BasePipeline"].endswith(".runtime")
    assert set(wiring.__all__) == set(wiring._EXPORT_MODULES)


def test_static_export_groups_cover_each_owner_module_all() -> None:
    """Static groups stay aligned with each owner module's public surface."""
    import bioetl.application.core.wiring as wiring

    for module_name in (
        "bioetl.application.core.wiring.factory",
        "bioetl.application.core.wiring.registry",
        "bioetl.application.core.wiring.runtime",
        "bioetl.application.core.wiring.transformer",
    ):
        owner = importlib.import_module(module_name)
        static_names = set(wiring._EXPORT_GROUPS[module_name])
        assert static_names == set(owner.__all__), module_name


@pytest.mark.parametrize(
    "export_name",
    [
        "BaseTransformer",
        "DefaultContractPolicy",
        "NoOpStructuralPolicy",
        "StructuralPolicyProtocol",
        "TransformerDependencyContext",
        "build_structural_policy",
    ],
)
def test_transformer_facade_exports_resolve(export_name: str) -> None:
    """Every transformer facade export is listed in __all__ and resolves on demand."""
    transformer = importlib.import_module("bioetl.application.core.wiring.transformer")
    assert export_name in transformer.__all__
    assert export_name in transformer._PUBLIC_EXPORTS
    value = getattr(transformer, export_name)
    assert value is not None
