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
"""Closeout guards for #10551 composition module-cap shrink."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
COMPOSITION = ROOT / "src" / "bioetl" / "composition"
BUDGET = ROOT / "configs" / "quality" / "package_cohesion_budget.yaml"

REMOVED_SHIMS = (
    "factories/pipeline/entity_type_extractor.py",
    "bootstrap/runtime/pipeline_runner_service_bootstrap.py",
    "bootstrap/runtime/composite_infrastructure_context.py",
    "bootstrap/runtime/classification_init.py",
    "factories/services/observability_api.py",
    "factories/storage/storage_factory.py",
    "_service_protocols.py",
    "providers/_registry_protocols.py",
)


def _composition_budget_row() -> dict[str, object]:
    payload = yaml.safe_load(BUDGET.read_text(encoding="utf-8"))
    rows = [
        row for row in payload["packages"] if row["path"] == "src/bioetl/composition"
    ]
    assert len(rows) == 1
    return rows[0]


def test_issue_10551_composition_module_count_below_previous_ceiling() -> None:
    """AUD-001: live composition modules stay under the shrink-only ratchet."""
    row = _composition_budget_row()
    live = len(list(COMPOSITION.rglob("*.py")))
    cap = int(row["max_modules"])

    assert cap == 295
    assert live == 291
    assert live <= cap
    assert str(row.get("linked_issue")) == "10551"
    # Headroom vs pre-fix ceiling of 300 and vs the live ratchet.
    assert (300 - live) >= 9
    assert (cap - live) >= 4


def test_issue_10551_removed_compatibility_shims_are_gone() -> None:
    """Pure re-export shims collapsed in #10551 must stay deleted."""
    present = [rel for rel in REMOVED_SHIMS if (COMPOSITION / rel).exists()]
    assert present == []
