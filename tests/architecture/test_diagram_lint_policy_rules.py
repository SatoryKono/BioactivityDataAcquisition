"""Architecture tests for diagram lint policy rules (ADR-040)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_lint_module() -> ModuleType:
    """Load scripts/lint_diagrams.py as a module for direct function testing."""
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "lint_diagrams.py"
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
        "style Domain fill:#FFF7ED,stroke:#F59E0B,stroke-width:2px",
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
