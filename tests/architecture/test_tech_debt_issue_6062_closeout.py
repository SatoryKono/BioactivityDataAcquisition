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
"""Architecture closeout guard for issue #6062."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
GOLD_WRITER = ROOT / "src/bioetl/infrastructure/storage/gold_writer.py"
CLOSEOUT = ROOT / "reports/quality/tech-debt-issue-6062-closeout.json"

_EXPECTED_RETAINED_IMPORTS = {
    # Function-scoped lazy loader renamed to PEP8 snake_case (scope id only;
    # import statement and monkeypatch surface write_deltalake unchanged).
    "delta_table: from deltalake import DeltaTable as _DeltaTable",
    "write_deltalake: from deltalake import write_deltalake as _write_deltalake",
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _function_scoped_imports(path: Path) -> list[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(module):
        for child in ast.iter_child_nodes(node):
            parents[child] = node

    imports: list[str] = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Import | ast.ImportFrom):
            continue

        parent = parents.get(node)
        scope: list[str] = []
        while parent is not None:
            if isinstance(
                parent, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
            ):
                scope.append(parent.name)
            parent = parents.get(parent)
        if not scope:
            continue

        scope_name = ".".join(reversed(scope))
        if isinstance(node, ast.ImportFrom):
            names = ", ".join(
                alias.name + (f" as {alias.asname}" if alias.asname else "")
                for alias in node.names
            )
            import_text = f"from {node.module} import {names}"
        else:
            names = ", ".join(
                alias.name + (f" as {alias.asname}" if alias.asname else "")
                for alias in node.names
            )
            import_text = f"import {names}"
        imports.append(f"{scope_name}: {import_text}")
    return imports


def test_issue_6062_closeout_artifact_records_improved_debt_outcome() -> None:
    payload = _load_json(CLOSEOUT)

    assert payload["schema_version"] == "tech-debt-issue-6062-closeout-v1"
    assert payload["issue"] == 6062
    assert payload["status"] == "closeable"
    assert payload["debt_outcome"] == "improved"
    assert payload["budget_growth_allowed"] is False
    assert payload["before"]["function_scoped_import_count"] == 12
    assert payload["after"]["function_scoped_import_count"] == 2
    assert payload["after"]["accidental_hidden_coupling_count"] == 0


def test_issue_6062_gold_writer_retains_only_optional_delta_lazy_imports() -> None:
    imports = set(_function_scoped_imports(GOLD_WRITER))

    assert imports == _EXPECTED_RETAINED_IMPORTS


def test_issue_6062_closeout_inventory_matches_live_gold_writer() -> None:
    payload = _load_json(CLOSEOUT)
    retained = payload["after"]["retained"]
    assert isinstance(retained, list)

    retained_imports = {
        f"{entry['scope']}: {entry['import']}"
        for entry in retained
        if isinstance(entry, dict)
    }

    assert retained_imports == set(_function_scoped_imports(GOLD_WRITER))
    assert {
        entry["classification"] for entry in retained if isinstance(entry, dict)
    } == {"optional dependency and compatibility patch-point"}
