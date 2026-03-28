"""Boundary tests for run-all helper/support compatibility seams."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


RUN_ALL_SUPPORT_SEAMS = ()


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
@pytest.mark.parametrize(("path_text", "target_module"), RUN_ALL_SUPPORT_SEAMS)
def test_run_all_support_seam_aliases_expected_canonical_module(
    path_text: str,
    target_module: str,
) -> None:
    """Each run-all support seam should alias exactly one canonical module."""
    assert _extract_alias_targets(Path(path_text)) == {target_module}
