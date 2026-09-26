"""Security regression tests for the legacy Mermaid operator codemod."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest

pytestmark = pytest.mark.repo_backed


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[4]
    module_path = repo_root / "scripts/diagrams/fix_mermaid_operators.py"
    spec = importlib.util.spec_from_file_location(
        "fix_mermaid_operators_security_module",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _diagram_root(tmp_path: Path) -> Path:
    root = tmp_path / "docs/02-architecture/diagrams"
    root.mkdir(parents=True)
    return root


def test_fix_file_updates_only_validated_diagram_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "_repo_root", lambda: tmp_path)
    diagram = _diagram_root(tmp_path) / "sequence.mmd"
    diagram.write_text("sequenceDiagram\nA ==>> B\n", encoding="utf-8")
    relative_diagram = diagram.relative_to(tmp_path)

    assert module.fix_file(relative_diagram, dry_run=False) == 1
    assert diagram.read_text(encoding="utf-8") == "sequenceDiagram\nA -->> B\n"


def test_fix_file_rejects_parent_traversal_and_non_diagram_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "_repo_root", lambda: tmp_path)
    _diagram_root(tmp_path)

    with pytest.raises(ValueError, match="parent traversal"):
        module.fix_file(Path("docs/02-architecture/diagrams/../escape.mmd"))
    with pytest.raises(ValueError, match="repository-relative"):
        module.fix_file(tmp_path / "outside.mmd")
    with pytest.raises(ValueError, match="outside"):
        module.fix_file(Path("outside.mmd"))
    with pytest.raises(ValueError, match="not a Mermaid"):
        module.fix_file(Path("docs/02-architecture/diagrams/diagram.txt"))


def test_fix_file_rejects_symlink_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "_repo_root", lambda: tmp_path)
    diagram_root = _diagram_root(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (outside / "sequence.mmd").write_text(
        "sequenceDiagram\nA ==>> B\n",
        encoding="utf-8",
    )
    link = diagram_root / "external"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(ValueError, match="outside"):
        module.fix_file(
            (link / "sequence.mmd").relative_to(tmp_path),
            dry_run=False,
        )
