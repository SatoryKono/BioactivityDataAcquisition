"""Boundary tests for shared CLI execution-policy compatibility seam."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


def _extract_alias_targets(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    targets: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "alias_module":
            continue
        if len(node.args) != 2:
            continue
        module_name_arg, target_arg = node.args
        if (
            not isinstance(module_name_arg, ast.Name)
            or module_name_arg.id != "__name__"
        ):
            continue
        if isinstance(target_arg, ast.Constant) and isinstance(target_arg.value, str):
            targets.add(target_arg.value)
    return targets


@pytest.mark.unit
def test_execution_policy_seam_aliases_expected_canonical_module() -> None:
    """The shared execution-policy seam should alias the canonical shared module."""
    assert _extract_alias_targets(
        Path("src/bioetl/interfaces/cli/commands/execution_policy.py")
    ) == {"bioetl.interfaces.cli.commands.domains.shared.execution_policy"}
