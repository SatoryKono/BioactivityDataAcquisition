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
"""ARCH-CR-05: runtime_builders run-manifest refs lazy facade."""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit


def test_run_manifest_refs_facade_exports_and_unknown() -> None:
    mod = importlib.import_module(
        "bioetl.composition.runtime_builders._run_manifest_refs"
    )
    assert callable(mod.control_plane_root)
    assert callable(mod.build_planned_artifacts)
    for name in (
        "DataRootMode",
        "is_explicit_data_root_configured",
        "resolve_data_root_mode",
    ):
        assert getattr(mod, name) is not None
    with pytest.raises(AttributeError, match="not_a_real_export_symbol_xyz"):
        mod.not_a_real_export_symbol_xyz
