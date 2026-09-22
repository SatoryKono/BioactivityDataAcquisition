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
"""Closeout guards for #10595 (AUD-002) composition utilisation shrink."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
COMPOSITION = ROOT / "src" / "bioetl" / "composition"
BUDGET = ROOT / "configs" / "quality" / "package_cohesion_budget.yaml"

# composition_util = live / max_modules must stay at or below this ceiling.
MAX_COMPOSITION_UTIL = 0.95

REMOVED_SHIMS = (
    "_json_types.py",
    "_service_types.py",
    "config_catalog.py",
    "bootstrap/service_registry_contracts.py",
    "bootstrap/runtime/_pipeline_bootstrap_lazy_dependencies.py",
    "bootstrap/runtime/composite_bootstrap_builders.py",
    "bootstrap/runtime/composite_support_service_builders.py",
    "bootstrap/runtime/composite_support_service_bundles.py",
    "contracts/services.py",
    "factories/_observability_wiring.py",
    "factories/pipeline/construction.py",
    "factories/pipeline/construction_types.py",
)

# Owner modules that absorbed the removed shims' callers.
OWNER_MODULES = (
    "bootstrap/runtime/composite_execution_support_builder.py",
    "bootstrap/runtime/composite_merge_dependency_builder.py",
    "bootstrap/runtime/composite_runtime_management_builder.py",
    "bootstrap/runtime/composite_merge_dependencies_bundle.py",
    "bootstrap/runtime/runtime_basics.py",
    "bootstrap/runtime/runner_assembly.py",
    "composite_catalog.py",
    "factories/observability_api.py",
)


def _composition_budget_row() -> dict[str, object]:
    payload = yaml.safe_load(BUDGET.read_text(encoding="utf-8"))
    rows = [
        row for row in payload["packages"] if row["path"] == "src/bioetl/composition"
    ]
    assert len(rows) == 1
    return rows[0]


def test_issue_10595_composition_util_at_or_below_ceiling() -> None:
    """AUD-002: composition_util = live / max_modules stays ≤ 0.95."""
    row = _composition_budget_row()
    live = len(list(COMPOSITION.rglob("*.py")))
    cap = int(row["max_modules"])

    assert cap <= 295, "max_modules is shrink-only; never raise it"
    assert live <= 280
    assert live <= cap
    assert live / cap <= MAX_COMPOSITION_UTIL
    assert str(row.get("linked_issue")) == "10595"


def test_issue_10595_removed_compatibility_shims_are_gone() -> None:
    """Pure re-export shims collapsed in #10595 must stay deleted."""
    present = [rel for rel in REMOVED_SHIMS if (COMPOSITION / rel).exists()]
    assert present == []


def test_issue_10595_owner_modules_remain() -> None:
    """Retargeted owners must still exist so callers resolve to real modules."""
    missing = [rel for rel in OWNER_MODULES if not (COMPOSITION / rel).exists()]
    assert missing == []
