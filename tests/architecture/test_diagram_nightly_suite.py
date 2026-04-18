"""Architecture tests for nightly diagram suite helpers."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "diagrams" / "run_diagram_nightly_suite.py"
    spec = importlib.util.spec_from_file_location(
        "diagram_nightly_suite_module", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_derive_png_path_replaces_svg_segment() -> None:
    module = _load_module()
    svg = Path("docs/02-architecture/diagrams/views/svg/demo.svg")

    png = module.derive_png_path(svg)

    assert png.parts[-3:] == ("views", "png", "demo.png")


def test_reorder_edge_lines_keeps_line_count() -> None:
    module = _load_module()
    lines = [
        "flowchart TB",
        "A --> B",
        "B --> C",
        "C --> D",
        "D --> E",
        "classDef x fill:#fff",
    ]

    reordered = module.reorder_edge_lines(lines, seed=1)

    assert len(reordered) == len(lines)
    assert sorted(reordered) == sorted(lines)


def test_inject_growth_node_adds_node_and_edge() -> None:
    module = _load_module()
    lines = [
        "flowchart TB",
        "A --> B",
    ]

    stressed = module.inject_growth_node(lines)

    assert any("__stress_node__" in line for line in stressed)
    assert any("--> __stress_node__" in line for line in stressed)


def test_parse_long_label_count_detects_long_and_dense_labels() -> None:
    module = _load_module()
    lines = [
        "flowchart LR",
        'A["very very very very long label text for test"] --> B["ok"]',
        'C["a<br/>b<br/>c<br/>d<br/>e"] --> D["ok"]',
    ]

    count = module.parse_long_label_count(lines, max_len=25, max_br=3)

    assert count >= 2


def test_load_manifest_rejects_parent_traversal_entries(tmp_path: Path) -> None:
    module = _load_module()
    manifest = tmp_path / "nightly.manifest"
    manifest.write_text("../escape.mmd\n", encoding="utf-8")

    try:
        module.load_manifest(manifest, (".mmd", ".mermaid"))
    except ValueError as exc:
        assert "must not escape the repository root" in str(exc)
    else:
        raise AssertionError("Expected manifest traversal validation to fail")


def test_load_manifest_rejects_option_like_entries(tmp_path: Path) -> None:
    module = _load_module()
    manifest = tmp_path / "nightly.manifest"
    manifest.write_text("-unsafe.mmd\n", encoding="utf-8")

    try:
        module.load_manifest(manifest, (".mmd", ".mermaid"))
    except ValueError as exc:
        assert "must not start with '-'" in str(exc)
    else:
        raise AssertionError("Expected option-like manifest validation to fail")


def test_git_pathspec_rejects_option_like_repo_relative_paths() -> None:
    module = _load_module()

    with pytest.raises(ValueError, match="must not start with '-'"):
        module._git_pathspec(Path("-unsafe.svg"))


def test_check_diag_t026_uses_repo_relative_git_pathspecs(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    recorded: dict[str, object] = {}

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        recorded["cmd"] = cmd
        recorded["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    issues = module.check_diag_t026([Path("docs/02-architecture/diagrams/views/svg/demo.svg")])

    assert issues == []
    assert recorded["cwd"] == module.REPO_ROOT
    assert recorded["cmd"] == [
        "git",
        "diff",
        "--name-only",
        "--",
        "docs/02-architecture/diagrams/views/svg/demo.svg",
    ]
