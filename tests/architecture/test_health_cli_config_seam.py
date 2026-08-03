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
"""Architecture gate: health CLI must not import infrastructure config directly."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

HEALTH_CLI_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "bioetl"
    / "interfaces"
    / "cli"
    / "commands"
    / "health.py"
)
FORBIDDEN_IMPORT_PREFIXES = ("bioetl.infrastructure.config",)


def _collect_import_targets(tree: ast.AST) -> list[str]:
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.append(node.module)
    return targets


@pytest.mark.architecture
def test_health_cli_does_not_import_infrastructure_config_directly() -> None:
    """Health command must route settings access through composition.health_api."""
    tree = ast.parse(HEALTH_CLI_PATH.read_text(encoding="utf-8"))
    violations = [
        target
        for target in _collect_import_targets(tree)
        if any(target.startswith(prefix) for prefix in FORBIDDEN_IMPORT_PREFIXES)
    ]
    assert not violations, (
        f"health.py must not import infrastructure config directly; found: {violations}"
    )
