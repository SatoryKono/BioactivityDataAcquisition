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
"""Architecture guard for strict Gold Pandera validator usage in runtime code."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "bioetl"
GOLD_VALIDATOR_NAMES = {"ContractAwareGoldValidator", "PanderaGoldValidator"}


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _strict_false_gold_validator_calls(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node) not in GOLD_VALIDATOR_NAMES:
            continue
        for keyword in node.keywords:
            if keyword.arg != "strict":
                continue
            if isinstance(keyword.value, ast.Constant) and keyword.value.value is False:
                relative = path.relative_to(ROOT).as_posix()
                violations.append(f"{relative}:{node.lineno}")
    return violations


def test_runtime_paths_do_not_construct_non_strict_gold_pandera_validators() -> None:
    """Gold validators in runtime paths must remain strict by default."""
    violations: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        violations.extend(_strict_false_gold_validator_calls(path))

    assert not violations, (
        "Non-strict Gold Pandera validators found in runtime paths:\n"
        + "\n".join(f"  - {item}" for item in violations)
    )
