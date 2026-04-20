"""Security regression tests for src/tools/differentiate_linkstyle.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
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


def test_write_validated_mermaid_text_rejects_parent_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "MERMAID_DIR", tmp_path)

    with pytest.raises(ValueError, match="outside"):
        module._write_validated_mermaid_text(tmp_path.parent / "escape.mmd", "content")


def test_write_validated_mermaid_text_accepts_mermaid_root_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "MERMAID_DIR", tmp_path)
    target = tmp_path / "ok.mmd"

    module._write_validated_mermaid_text(target, "content")

    assert target.read_text(encoding="utf-8") == "content"
