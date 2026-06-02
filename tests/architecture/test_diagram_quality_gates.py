"""Architecture tests for diagram regression quality gates (DIAG-T018..T023)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


pytestmark = pytest.mark.architecture


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "diagrams" / "check_diagram_quality_gates.py"
    spec = importlib.util.spec_from_file_location(
        "diagram_quality_gates_module", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_line_style_guide_rejects_forbidden_operator() -> None:
    module = _load_module()
    lines = [
        "flowchart TB",
        "A --- B",
    ]

    issues = module.check_line_style_guide(Path("docs/sample.mmd"), lines)

    assert any(issue.rule_id == "DIAG-T018" for issue in issues)


def test_large_diagram_requires_decomposition_and_legend(tmp_path: Path) -> None:
    module = _load_module()
    diagram = tmp_path / "99-large-diagram.mmd"
    diagram.write_text(
        "\n".join(
            [
                "%% @nodes 32",
                "flowchart TB",
                "A --> B",
            ]
        ),
        encoding="utf-8",
    )

    lines = diagram.read_text(encoding="utf-8").splitlines()
    decomposition_issues = module.check_large_diagram_decomposition(
        diagram, lines, threshold=30
    )
    legend_issues = module.check_large_diagram_legend(diagram, lines, threshold=30)

    assert any(issue.rule_id == "DIAG-T020" for issue in decomposition_issues)
    assert any(issue.rule_id == "DIAG-T021" for issue in legend_issues)


def test_label_quality_warns_for_long_and_dense_labels() -> None:
    module = _load_module()
    lines = [
        "flowchart LR",
        'A["This label is intentionally very long to exceed the threshold and should trigger a warning"] --> B["ok"]',
        'C["line1<br/>line2<br/>line3<br/>line4<br/>line5<br/>line6"] --> D["ok"]',
    ]

    issues = module.check_label_quality(
        Path("docs/sample.mmd"),
        lines,
        max_label_length=40,
        max_br=4,
    )

    assert any(issue.rule_id == "DIAG-T022" for issue in issues)
    assert any(issue.rule_id == "DIAG-T023" for issue in issues)


def test_classdef_coverage_warns_when_missing() -> None:
    module = _load_module()
    lines = [
        "flowchart TB",
        "A --> B",
    ]

    issues = module.check_classdef_coverage(Path("docs/sample.mmd"), lines)

    assert any(issue.rule_id == "DIAG-T019" for issue in issues)


def test_write_report_output_rejects_parent_traversal() -> None:
    module = _load_module()

    with pytest.raises(ValueError, match="outside"):
        module._write_report_output(Path("../outside/report.json"), "{}\n")
