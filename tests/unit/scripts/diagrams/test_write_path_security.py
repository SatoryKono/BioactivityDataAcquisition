"""Security regression tests for diagram write helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest


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
    return Path(__file__).resolve().parents[4]


def test_fix_pagebreaks_rejects_parent_traversal_on_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        _repo_root() / "scripts" / "diagrams" / "fix_pagebreaks_in_bundles.py",
        "fix_pagebreaks_security_module",
    )
    monkeypatch.setattr(module, "DIAGRAM_ROOT", tmp_path)

    with pytest.raises(ValueError, match="parent traversal"):
        module._write_bundle_text(Path("../escape.bundle.md"), "content")


def test_fix_pagebreaks_rejects_absolute_path_on_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module(
        _repo_root() / "scripts" / "diagrams" / "fix_pagebreaks_in_bundles.py",
        "fix_pagebreaks_security_module_absolute",
    )
    monkeypatch.setattr(module, "DIAGRAM_ROOT", tmp_path)

    with pytest.raises(ValueError, match="absolute path"):
        module._write_bundle_text(tmp_path / "escape.bundle.md", "content")


def test_uniform_sizes_rejects_parent_traversal_on_write() -> None:
    module = _load_module(
        _repo_root() / "scripts" / "diagrams" / "uniform_diagram_sizes.py",
        "uniform_diagram_sizes_security_module",
    )

    with pytest.raises(ValueError, match="parent traversal"):
        module._write_repo_text(Path("../escape.mmd"), "content")


def test_uniform_sizes_rejects_absolute_path_on_write(tmp_path: Path) -> None:
    module = _load_module(
        _repo_root() / "scripts" / "diagrams" / "uniform_diagram_sizes.py",
        "uniform_diagram_sizes_security_module_absolute",
    )

    with pytest.raises(ValueError, match="absolute path"):
        module._write_repo_text(tmp_path / "escape.mmd", "content")
