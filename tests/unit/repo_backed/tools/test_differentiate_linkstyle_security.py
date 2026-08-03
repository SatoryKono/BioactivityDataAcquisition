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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Security regression tests for src/tools/differentiate_linkstyle.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest

pytestmark = pytest.mark.repo_backed


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[4]
    module_path = repo_root / "src" / "tools" / "differentiate_linkstyle.py"
    spec = importlib.util.spec_from_file_location(
        "differentiate_linkstyle_security_module",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ensure_path_within_root_rejects_write_outside_mermaid_root(
    tmp_path: Path,
) -> None:
    """Path guard rejects targets outside the provided root (root is explicit)."""
    module = _load_module()
    # MERMAID_DIR is re-exported for patchability, but this guard takes root explicitly.
    assert hasattr(module, "MERMAID_DIR")

    with pytest.raises(ValueError, match="outside"):
        module._ensure_path_within_root(tmp_path.parent / "escape.mmd", tmp_path)


def test_write_validated_mermaid_text_accepts_mermaid_root_file(
    tmp_path: Path,
) -> None:
    module = _load_module()
    target = module._ensure_path_within_root(tmp_path / "ok.mmd", tmp_path)
    # Ensure parent exists so write path exercises validated IO.
    target.parent.mkdir(parents=True, exist_ok=True)

    module._write_validated_mermaid_text(target, "content")

    assert target.read_text(encoding="utf-8") == "content"
