"""Architecture and governance guards for passport projections."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_runtime_does_not_import_passport_tooling() -> None:
    violations: list[str] = []
    for path in sorted((ROOT / "src/bioetl").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(name.startswith("scripts.docs.passports") for name in names):
                violations.append(path.relative_to(ROOT).as_posix())
    assert violations == []


def test_committed_passport_completeness_is_exact() -> None:
    report = json.loads(
        (
            ROOT
            / "docs/04-reference/passports/completeness-report.json"
        ).read_text(encoding="utf-8")
    )
    assert report["counts"] == {
        "composite": 5,
        "pipeline": 22,
        "total": 54,
        "workflow": 27,
    }
    assert report["orphan_passports"] == []
    assert report["duplicate_typed_identities"] == []
    assert report["blocking_diagnostics"] == 0


def test_passport_cli_is_wired_into_docs_governance() -> None:
    docs_router = (ROOT / "scripts/docs/__main__.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/docs.yml").read_text(encoding="utf-8")
    assert '"passports": "scripts.docs.passports.cli"' in docs_router
    assert "python -m scripts.docs passports check" in workflow


def test_reconciliation_ownership_is_explicitly_decided() -> None:
    decision = (
        ROOT
        / "docs/02-architecture/decisions/ADR-055-workflow-reconciliation-data-step-ownership.md"
    ).read_text(encoding="utf-8")
    assert "**Status:** Accepted" in decision
    assert "data_plane_transformation" in decision
    assert "commit_pending_confirmation" in decision
