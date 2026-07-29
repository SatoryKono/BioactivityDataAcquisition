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
"""Unit tests for the retained runtime bootstrap compatibility hook."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.composition.bootstrap.runtime.pipeline import (
    apply_runtime_compatibility_patches,
)

pytestmark = pytest.mark.unit


def test_apply_runtime_compatibility_patches_is_retained_noop() -> None:
    """Runtime compatibility hook stays public but no longer owns Pandera logic."""
    assert apply_runtime_compatibility_patches() is False


def test_runtime_compatibility_hook_no_longer_imports_pandera_shim() -> None:
    """The Pandera-specific compatibility shim must stay removed."""
    pipeline_source = Path(
        "src/bioetl/composition/bootstrap/runtime/pipeline.py"
    ).read_text(encoding="utf-8")

    assert "pandera_compat" not in pipeline_source
    assert "validate_supported_pandera_runtime" not in pipeline_source
