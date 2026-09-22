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
"""Closeout guards for #10552 domain/aggregates hold-flat + Batch sunset."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
AGGREGATES = ROOT / "src" / "bioetl" / "domain" / "aggregates"
BUDGET = ROOT / "configs" / "quality" / "package_cohesion_budget.yaml"
CLASSIFICATION = ROOT / "configs" / "quality" / "domain_aggregate_classification.yaml"
LAZY_INVENTORY = ROOT / "configs" / "quality" / "public_lazy_facade_inventory.yaml"
BATCH_MODULE = AGGREGATES / "batch.py"


def _aggregates_budget_row() -> dict[str, object]:
    payload = yaml.safe_load(BUDGET.read_text(encoding="utf-8"))
    rows = [
        row
        for row in payload["packages"]
        if row["path"] == "src/bioetl/domain/aggregates"
    ]
    assert len(rows) == 1
    return rows[0]


def test_issue_10552_domain_aggregates_hold_flat_at_ceiling() -> None:
    """AUD-002: package stays at shrink-only ceiling until mixin merge fits 305 LOC."""
    row = _aggregates_budget_row()
    py_files = sorted(AGGREGATES.glob("*.py"))
    live_count = len(py_files)

    assert int(row["max_modules"]) == 8
    assert int(row["target_modules"]) == 8
    assert str(row["hold_flat_issue"]) == "10552"
    assert live_count == int(row["max_modules"])
    assert live_count <= int(row["max_modules"])


def test_issue_10552_batch_compatibility_getattr_removed() -> None:
    """ADR-059 one-release Batch re-export sunset (#10552)."""
    tree = ast.parse(BATCH_MODULE.read_text(encoding="utf-8"), filename=str(BATCH_MODULE))
    getattr_names = [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "__getattr__"
    ]
    assert getattr_names == []

    inventory = yaml.safe_load(LAZY_INVENTORY.read_text(encoding="utf-8"))
    batch_rows = [
        facade
        for facade in inventory["facades"]
        if facade["path"] == "src/bioetl/domain/aggregates/batch.py"
    ]
    assert batch_rows == []


def test_issue_10552_batch_root_is_private_aggregate_module() -> None:
    """Classification points Batch root at _batch_aggregate after sunset."""
    payload = yaml.safe_load(CLASSIFICATION.read_text(encoding="utf-8"))
    batch_row = next(
        row for row in payload["true_aggregates"] if row["aggregate"] == "Batch"
    )
    assert batch_row["root_module"] == (
        "src/bioetl/domain/aggregates/_batch_aggregate.py"
    )


def test_issue_10552_no_src_batch_module_batch_root_imports() -> None:
    """Production src must not import Batch from the retired batch.py shim."""
    forbidden = "from bioetl.domain.aggregates.batch import"
    violations: list[str] = []
    src_root = ROOT / "src" / "bioetl"
    for path in sorted(src_root.rglob("*.py")):
        if path.resolve().is_relative_to(AGGREGATES.resolve()):
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if forbidden not in stripped:
                continue
            # Value-object imports (BatchRecord / BatchStatus) remain valid.
            if "BatchRecord" in stripped or "BatchStatus" in stripped:
                if " import Batch," in stripped or stripped.endswith(" import Batch"):
                    violations.append(f"{path.relative_to(ROOT)}:{lineno}:{stripped}")
                continue
            if "Batch" in stripped:
                violations.append(f"{path.relative_to(ROOT)}:{lineno}:{stripped}")
    assert violations == []
