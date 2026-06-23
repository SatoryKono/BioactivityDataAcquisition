"""Security regression tests for diagram write helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest

pytestmark = pytest.mark.repo_backed


def _load_module(module_path: Path, module_name: str) -> ModuleType:
    module_dir = str(module_path.parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def test_fix_pagebreaks_rejects_write_outside_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        _repo_root() / "scripts" / "diagrams" / "fix_pagebreaks_in_bundles.py",
        "fix_pagebreaks_security_module",
    )
    monkeypatch.setattr(module, "DIAGRAM_ROOT", tmp_path)

    with pytest.raises(ValueError, match="outside"):
        safe_path = module._safe_bundle_path(tmp_path.parent / "escape.bundle.md")
        module._write_bundle_text(safe_path, "content")


def test_fix_pagebreaks_accepts_validated_root_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        _repo_root() / "scripts" / "diagrams" / "fix_pagebreaks_in_bundles.py",
        "fix_pagebreaks_security_module_absolute",
    )
    monkeypatch.setattr(module, "DIAGRAM_ROOT", tmp_path)
    target = module._safe_bundle_path(tmp_path / "bundle.md")

    module._write_bundle_text(target, "content")

    assert target.read_text(encoding="utf-8") == "content"


def test_uniform_sizes_rejects_write_outside_repo(tmp_path: Path) -> None:
    module = _load_module(
        _repo_root() / "scripts" / "diagrams" / "uniform_diagram_sizes.py",
        "uniform_diagram_sizes_security_module",
    )

    with pytest.raises(ValueError, match="outside"):
        safe_path = module._ensure_repo_path(tmp_path.parent / "escape.mmd")
        module._write_repo_text(safe_path, "content")


def test_uniform_sizes_accepts_validated_repo_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        _repo_root() / "scripts" / "diagrams" / "uniform_diagram_sizes.py",
        "uniform_diagram_sizes_security_module_absolute",
    )
    monkeypatch.setattr(module, "SCRIPT_DIR", tmp_path)
    target = module._ensure_repo_path(tmp_path / "tmp_uniform_sizes_test.mmd")
    try:
        module._write_repo_text(target, "content")
        assert target.read_text(encoding="utf-8") == "content"
    finally:
        if target.exists():
            target.unlink()
