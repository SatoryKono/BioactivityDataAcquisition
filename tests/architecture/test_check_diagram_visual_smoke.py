"""Architecture tests for visual smoke manifest validation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "diagrams" / "check_diagram_visual_smoke.py"
    spec = importlib.util.spec_from_file_location(
        "check_diagram_visual_smoke_module", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_load_manifest_rejects_absolute_entries(tmp_path: Path) -> None:
    module = _load_module()
    manifest = tmp_path / "visual.manifest"
    manifest.write_text("/tmp/outside.svg\n", encoding="utf-8")

    try:
        module.load_manifest(manifest)
    except ValueError as exc:
        assert "must be relative" in str(exc)
    else:
        raise AssertionError("Expected absolute manifest validation to fail")


def test_load_manifest_rejects_parent_traversal_entries(tmp_path: Path) -> None:
    module = _load_module()
    manifest = tmp_path / "visual.manifest"
    manifest.write_text("../escape.svg\n", encoding="utf-8")

    try:
        module.load_manifest(manifest)
    except ValueError as exc:
        assert "must not escape the repository root" in str(exc)
    else:
        raise AssertionError("Expected traversal manifest validation to fail")
