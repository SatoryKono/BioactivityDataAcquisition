"""Boundary tests for run helper/support compatibility seams."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


RUN_SUPPORT_SEAMS = (
    (
        "src/bioetl/interfaces/cli/commands/run_helpers.py",
        "bioetl.interfaces.cli.commands.domains.run.support",
    ),
    (
        "src/bioetl/interfaces/cli/commands/run_runtime_helpers.py",
        "bioetl.interfaces.cli.commands.domains.run.runtime_helpers",
    ),
    (
        "src/bioetl/interfaces/cli/commands/run_result_presenter.py",
        "bioetl.interfaces.cli.commands.domains.run.result_presenter",
    ),
    (
        "src/bioetl/interfaces/cli/commands/run_result_flow_helpers.py",
        "bioetl.interfaces.cli.commands.domains.run.result_flow",
    ),
    (
        "src/bioetl/interfaces/cli/commands/run_service_access.py",
        "bioetl.interfaces.cli.commands.domains.run.service_access",
    ),
    (
        "src/bioetl/interfaces/cli/commands/run_command_policy.py",
        "bioetl.interfaces.cli.commands.domains.run.command_policy",
    ),
)


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
@pytest.mark.parametrize(("path_text", "target_module"), RUN_SUPPORT_SEAMS)
def test_run_support_seam_aliases_expected_canonical_module(
    path_text: str,
    target_module: str,
) -> None:
    """Each run support seam should alias exactly one canonical domains.run module."""
    assert _extract_alias_targets(Path(path_text)) == {target_module}
