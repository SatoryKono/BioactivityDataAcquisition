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
"""Tests for the composition.services package-root surface."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.unit
def test_services_package_root_retains_only_versioning_namespace() -> None:
    """Package root should not re-export versioning helpers directly."""
    module = importlib.import_module("bioetl.composition.services")

    assert module.__all__ == ["versioning"]
    assert hasattr(module, "versioning")
    for removed_name in (
        "compute_config_hash",
        "get_code_revision_provenance",
        "get_dependency_lock_hash",
        "get_git_commit",
        "get_pipeline_version",
    ):
        assert removed_name not in dir(module)
        with pytest.raises(AttributeError):
            getattr(module, removed_name)
