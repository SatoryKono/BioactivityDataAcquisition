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
"""Architecture guardrails for quarantine CLI seam ownership."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
QUARANTINE_CLI_PATH = (
    ROOT / "src" / "bioetl" / "interfaces" / "cli" / "commands" / "quarantine.py"
)
FORBIDDEN_IMPORT_PREFIXES = (
    "bioetl.interfaces.cli.commands.health",
    "bioetl.interfaces.cli.commands.domains.health",
)
REQUIRED_IMPORT_PREFIXES = (
    "bioetl.interfaces.cli.commands.domains.quarantine.runtime_access",
    "bioetl.interfaces.cli.commands.domains.quarantine.server_backend",
)


def _collect_import_targets(tree: ast.AST) -> list[str]:
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.append(node.module)
    return targets


@pytest.mark.architecture
def test_quarantine_cli_does_not_import_health_owned_cli_seams() -> None:
    """Quarantine CLI must use quarantine-owned seams instead of health-owned ones."""
    tree = ast.parse(QUARANTINE_CLI_PATH.read_text(encoding="utf-8"))
    imports = _collect_import_targets(tree)
    violations = [
        target
        for target in imports
        if any(target.startswith(prefix) for prefix in FORBIDDEN_IMPORT_PREFIXES)
    ]
    assert not violations, (
        f"quarantine.py must not import health-owned CLI seams; found: {violations}"
    )
    for prefix in REQUIRED_IMPORT_PREFIXES:
        assert any(target.startswith(prefix) for target in imports), (
            "quarantine.py must route through quarantine-owned CLI seams; "
            f"missing import prefix {prefix}"
        )
