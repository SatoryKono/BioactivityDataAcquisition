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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "MERMAID_DIR", tmp_path)

    with pytest.raises(ValueError, match="outside"):
        module._ensure_path_within_root(tmp_path.parent / "escape.mmd", tmp_path)


def test_write_validated_mermaid_text_accepts_mermaid_root_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "MERMAID_DIR", tmp_path)
    target = module._ensure_path_within_root(tmp_path / "ok.mmd", tmp_path)

    module._write_validated_mermaid_text(target, "content")

    assert target.read_text(encoding="utf-8") == "content"
