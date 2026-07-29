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
"""Architecture tests for diagram lint policy rules (ADR-040)."""

from __future__ import annotations

import pytest

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


pytestmark = pytest.mark.architecture


def _load_lint_module() -> ModuleType:
    """Load scripts/diagrams/lint_diagrams.py for direct function testing."""
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "diagrams" / "lint_diagrams.py"
    spec = importlib.util.spec_from_file_location("lint_diagrams_module", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_colour_rule_flags_deprecated_palette() -> None:
    """COLOUR-001 must flag legacy pre-ADR palette in style/classDef lines."""
    lint = _load_lint_module()
    lines = [
        "flowchart TB",
        "style Domain fill:#F3E5F5,stroke:#1565C0,stroke-width:2px",
    ]

    issues = lint.check_colour_policy(Path("docs/02-architecture/demo.mmd"), lines)
    rules = {issue.rule for issue in issues}

    assert "COLOUR-001" in rules


def test_emoji_rule_flags_subgraph_prefix_icons() -> None:
    """COLOUR-002 must reject emoji prefixes in subgraph labels."""
    lint = _load_lint_module()
    lines = [
        "flowchart TB",
        'subgraph Domain["🟡 Domain Layer"]',
        "end",
    ]

    issues = lint.check_subgraph_emoji(Path("docs/02-architecture/demo.mmd"), lines)
    rules = {issue.rule for issue in issues}

    assert "COLOUR-002" in rules


def test_size_rules_apply_and_reference_full_is_exempt() -> None:
    """SIZE-001/SIZE-002 should trigger, but *-full.mermaid stays exempt."""
    lint = _load_lint_module()

    warning = lint.check_node_count_policy(
        Path("docs/02-architecture/mmd-diagrams/architecture/sample.mmd"),
        ["%% @nodes 29", "flowchart TB", "A-->B"],
    )
    error = lint.check_node_count_policy(
        Path("docs/02-architecture/mmd-diagrams/architecture/sample.mmd"),
        ["%% @nodes 39", "flowchart TB", "A-->B"],
    )
    full_view_exempt = lint.check_node_count_policy(
        Path("docs/02-architecture/diagrams/mermaid/01-high-level-full.mermaid"),
        ["%% @nodes 99", "flowchart TB", "A-->B"],
    )

    assert any(issue.rule == "SIZE-002" for issue in warning)
    assert any(issue.rule == "SIZE-001" for issue in error)
    assert full_view_exempt == []


def test_size_hard_limit_downgrades_when_decomposed_siblings_exist(
    tmp_path: Path,
) -> None:
    """SIZE-003 warning should replace SIZE-001 for decomposed canonical .mmd."""
    lint = _load_lint_module()
    full = tmp_path / "01-big-diagram.mmd"
    sibling = tmp_path / "01a-big-diagram-slice.mmd"
    sibling.write_text("flowchart TB\nA-->B\n", encoding="utf-8")

    issues = lint.check_node_count_policy(
        full,
        ["%% @nodes 46", "flowchart TB", "A-->B"],
    )
    rules = {issue.rule for issue in issues}

    assert "SIZE-003" in rules
    assert "SIZE-001" not in rules


def test_link_semantics_warns_when_dense_flow_uses_single_arrow_type() -> None:
    """LINK-001 should warn when dense flowchart uses only one arrow semantic style."""
    lint = _load_lint_module()
    lines = [
        "flowchart TB",
        "A-->B",
        "B-->C",
        "C-->D",
        "D-->E",
        "E-->F",
        "F-->G",
        "G-->H",
        "H-->I",
    ]

    issues = lint.check_link_semantics(
        Path("docs/02-architecture/mmd-diagrams/architecture/sample.mmd"),
        lines,
    )

    assert any(issue.rule == "LINK-001" for issue in issues)


def test_link_semantics_passes_when_arrows_are_semantically_mixed() -> None:
    """LINK-001 should not warn when semantic arrow styles are mixed."""
    lint = _load_lint_module()
    lines = [
        "flowchart TB",
        "A-->B",
        "B-.->C",
        "C==>D",
        "D-->E",
        "E-.->F",
        "F==>G",
        "G-->H",
        "H-.->I",
    ]

    issues = lint.check_link_semantics(
        Path("docs/02-architecture/mmd-diagrams/architecture/sample.mmd"),
        lines,
    )

    assert not any(issue.rule == "LINK-001" for issue in issues)


def test_linkstyle_index_fragility_warns_for_large_index_groups() -> None:
    """LINK-002 should warn on fragile singleton-index linkStyle patterns."""
    lint = _load_lint_module()
    lines = [
        "flowchart TB",
        "A-->B",
        "B-->C",
        "linkStyle 0 stroke:#1E293B,stroke-width:2px",
        "linkStyle 1 stroke:#1E293B,stroke-width:2px",
        "linkStyle 2 stroke:#1E293B,stroke-width:2px",
        "linkStyle 3 stroke:#1E293B,stroke-width:2px",
        "linkStyle 4 stroke:#1E293B,stroke-width:2px",
        "linkStyle 5 stroke:#1E293B,stroke-width:2px",
        "linkStyle 6 stroke:#1E293B,stroke-width:2px",
        "linkStyle 7 stroke:#1E293B,stroke-width:2px",
        "linkStyle 8 stroke:#1E293B,stroke-width:2px",
        "linkStyle 9 stroke:#1E293B,stroke-width:2px",
        "linkStyle 10 stroke:#1E293B,stroke-width:2px",
        "linkStyle 11 stroke:#1E293B,stroke-width:2px",
    ]

    issues = lint.check_linkstyle_index_fragility(
        Path("docs/02-architecture/mmd-diagrams/architecture/sample.mmd"),
        lines,
    )

    assert any(issue.rule == "LINK-002" for issue in issues)


def test_label_readability_warns_on_long_lines_and_br_padding() -> None:
    """LABEL-001/003 should warn on overlong label lines and <br/> padding."""
    lint = _load_lint_module()
    lines = [
        "flowchart TB",
        'A["VeryLongComponentNameWithoutEnoughBreaks makes labels unreadable in PNG output"]',
        'B["Header<br/><br/><br/>Body"]',
    ]

    issues = lint.check_label_readability(
        Path("docs/02-architecture/mmd-diagrams/architecture/sample.mmd"),
        lines,
    )
    rules = {issue.rule for issue in issues}

    assert "LABEL-001" in rules
    assert "LABEL-003" in rules


def test_label_readability_warns_on_too_many_node_lines() -> None:
    """LABEL-002 should warn when node label has too many logical lines."""
    lint = _load_lint_module()
    lines = [
        "flowchart TB",
        ('A["H<br/>1<br/>2<br/>3<br/>4<br/>5<br/>6<br/>7<br/>8<br/>9"]'),
    ]

    issues = lint.check_label_readability(
        Path("docs/02-architecture/mmd-diagrams/architecture/sample.mmd"),
        lines,
    )

    assert any(issue.rule == "LABEL-002" for issue in issues)


def test_class_rule_flags_unescaped_dunder_methods() -> None:
    """CLASS-001 should warn when dunder methods are not escaped."""
    lint = _load_lint_module()
    lines = [
        "classDiagram",
        "class X {",
        "+__aenter__() Self",
        "}",
    ]

    issues = lint.check_class_method_render_safety(
        Path("docs/02-architecture/mmd-diagrams/class-diagrams/sample.mmd"),
        lines,
    )

    assert any(issue.rule == "CLASS-001" for issue in issues)


def test_class_rule_flags_mixed_return_notation() -> None:
    """CLASS-002 should warn when return notation is mixed in one class diagram."""
    lint = _load_lint_module()
    lines = [
        "classDiagram",
        "class X {",
        "+foo() : bool",
        "+bar() bool",
        "}",
    ]

    issues = lint.check_class_method_render_safety(
        Path("docs/02-architecture/mmd-diagrams/class-diagrams/sample.mmd"),
        lines,
    )

    assert any(issue.rule == "CLASS-002" for issue in issues)


def test_class_rule_flags_overlong_method_signature() -> None:
    """CLASS-003 should warn when method signature length exceeds readability threshold."""
    lint = _load_lint_module()
    lines = [
        "classDiagram",
        "class X {",
        (
            "+very_long_method_name_with_many_parameters("
            "parameter_one, parameter_two, parameter_three, parameter_four"
            ") : ReturnValue"
        ),
        "}",
    ]

    issues = lint.check_class_method_render_safety(
        Path("docs/02-architecture/mmd-diagrams/class-diagrams/sample.mmd"),
        lines,
    )

    assert any(issue.rule == "CLASS-003" for issue in issues)
