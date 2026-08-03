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


def test_canonical_wiring_export_groups_are_loaded_from_declared_submodules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lazy facade derives exports deterministically from owner modules."""
    import types

    import bioetl.application.core.wiring as wiring

    calls: list[str] = []

    def _fake_import_module(module_name: str) -> object:
        calls.append(module_name)
        return types.SimpleNamespace(__all__=(f"{module_name}.export",))

    monkeypatch.setattr(
        wiring,
        "_WIRING_SUBMODULES",
        ("bioetl.owner.one", "bioetl.owner.two"),
    )
    monkeypatch.setattr(wiring, "import_module", _fake_import_module)

    assert wiring._build_export_groups() == {
        "bioetl.owner.one": ("bioetl.owner.one.export",),
        "bioetl.owner.two": ("bioetl.owner.two.export",),
    }
    assert calls == ["bioetl.owner.one", "bioetl.owner.two"]
