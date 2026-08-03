# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for scripts/diagrams/fix_mermaid_operators.py."""

from __future__ import annotations

import importlib.util

import pytest
import sys
from pathlib import Path
from types import ModuleType


pytestmark = pytest.mark.architecture


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "diagrams" / "fix_mermaid_operators.py"
    spec = importlib.util.spec_from_file_location(
        "fix_mermaid_operators_module", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_check_file_flags_only_class_and_sequence_diagrams(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "_repo_root", lambda: tmp_path)

    class_diagram = tmp_path / "class-demo.mmd"
    class_diagram.write_text(
        "\n".join(
            [
                "classDiagram",
                "A ==> B",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    sequence_diagram = tmp_path / "sequence-demo.mmd"
    sequence_diagram.write_text(
        "\n".join(
            [
                "sequenceDiagram",
                "A ==>> B: response",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    flowchart = tmp_path / "flow-demo.mmd"
    flowchart.write_text(
        "\n".join(
            [
                "flowchart TD",
                "A ==> B",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    class_result = module.check_file(class_diagram)
    sequence_result = module.check_file(sequence_diagram)
    flow_result = module.check_file(flowchart)

    assert [issue.operator for issue in class_result.issues] == ["==>"]
    assert [issue.operator for issue in sequence_result.issues] == ["==>>"]
    assert flow_result.issues == []


def test_fix_file_rewrites_invalid_arrows_in_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "_repo_root", lambda: tmp_path)

    diagram = tmp_path / "sequence-demo.mmd"
    diagram.write_text(
        "\n".join(
            [
                "sequenceDiagram",
                "A ==> B: request",
                "B ==>> A: response",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    replacements = module.fix_file(diagram, dry_run=False)
    content = diagram.read_text(encoding="utf-8")

    assert replacements == 2
    assert "==>" not in content
    assert "==>>" not in content
    assert "A --> B: request" in content
    assert "B -->> A: response" in content


def test_fix_file_dry_run_does_not_modify_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "_repo_root", lambda: tmp_path)

    diagram = tmp_path / "class-demo.mmd"
    original = "\n".join(["classDiagram", "A ==> B"]) + "\n"
    diagram.write_text(original, encoding="utf-8")

    replacements = module.fix_file(diagram, dry_run=True)
    content_after = diagram.read_text(encoding="utf-8")

    assert replacements == 1
    assert content_after == original


def test_fix_file_rejects_paths_outside_repo(tmp_path: Path) -> None:
    module = _load_module()
    diagram = tmp_path / "outside-repo.mmd"
    diagram.write_text("sequenceDiagram\nA ==> B\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside"):
        module.fix_file(diagram, dry_run=False)


def test_fix_file_rejects_parent_traversal_relative_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "_repo_root", lambda: tmp_path)

    with pytest.raises(ValueError, match="parent traversal"):
        module.fix_file(Path("../escape.mmd"), dry_run=False)


@pytest.mark.slow
def test_repo_regression_has_no_thick_arrows_in_class_sequence_sources() -> None:
    module = _load_module()
    repo_root = Path(__file__).resolve().parents[2]
    scope = repo_root / "docs" / "02-architecture" / "diagrams"

    files = sorted(list(scope.rglob("*.mmd")) + list(scope.rglob("*.mermaid")))
    offending: list[str] = []
    for path in files:
        result = module.check_file(path)
        if result.issues:
            for issue in result.issues:
                rel = path.relative_to(repo_root)
                offending.append(f"{rel}:{issue.line_no}:{issue.operator}")

    assert not offending, "Found invalid thick arrows:\n" + "\n".join(offending)
