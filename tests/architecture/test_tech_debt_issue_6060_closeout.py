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
"""Architecture closeout guard for issue #6060."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.qa.hotspot_family_metrics import (
    count_internal_fan_in,
    iter_family_python_files,
    load_scorecard,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports/quality/tech-debt-issue-6060-closeout.json"
HOTSPOT_BASELINE = ROOT / "reports/quality/hotspot-family-baseline.json"


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _hotspot_family_row(path: Path, name: str) -> dict[str, object]:
    payload = _load_json(path)
    families = payload["families"]
    assert isinstance(families, list)
    row = next(
        family
        for family in families
        if isinstance(family, dict) and family.get("name") == name
    )
    return row


def _scorecard_family_row(name: str) -> dict[str, object]:
    scorecard = load_scorecard()
    ratchets = scorecard["hotspot_family_ratchets"]
    assert isinstance(ratchets, dict)
    families = ratchets["families"]
    assert isinstance(families, list)
    row = next(
        family
        for family in families
        if isinstance(family, dict) and family.get("name") == name
    )
    return row


def _live_family_fan_in(name: str) -> tuple[int, str | None]:
    family = _scorecard_family_row(name)
    path_prefixes = family["path_prefixes"]
    assert isinstance(path_prefixes, list)
    files = iter_family_python_files(
        path_prefixes=[prefix for prefix in path_prefixes if isinstance(prefix, str)]
    )
    return count_internal_fan_in(files=files)


def test_issue_6060_closeout_artifact_records_improved_debt_outcome() -> None:
    payload = _load_json(CLOSEOUT)

    assert payload["schema_version"] == "tech-debt-issue-6060-closeout-v1"
    assert payload["issue"] == 6060
    assert payload["status"] == "closeable"
    assert payload["debt_outcome"] == "improved"
    assert payload["budget_growth_allowed"] is False


def test_issue_6060_composition_runtime_builder_fan_in_has_headroom() -> None:
    baseline = _hotspot_family_row(HOTSPOT_BASELINE, "composition_runtime_builders")
    scorecard = _scorecard_family_row("composition_runtime_builders")
    budgets = baseline["bounded_growth_budgets"]
    scorecard_budgets = scorecard["bounded_growth_budgets"]
    scorecard_metrics = scorecard["metrics"]
    assert isinstance(budgets, dict)
    assert isinstance(scorecard_budgets, dict)
    assert isinstance(scorecard_metrics, dict)

    live_fan_in, live_module = _live_family_fan_in("composition_runtime_builders")

    assert live_fan_in <= 4
    assert baseline["max_internal_fan_in"] == live_fan_in
    assert scorecard_metrics["max_internal_fan_in"] == live_fan_in
    assert baseline["max_internal_fan_in_module"] == live_module
    assert scorecard_metrics["max_internal_fan_in_module"] == live_module
    assert budgets["max_internal_fan_in"] <= 5
    assert budgets["max_internal_fan_in"] >= live_fan_in
    assert scorecard_budgets["max_internal_fan_in"] <= 5
    assert scorecard_budgets["max_internal_fan_in"] >= live_fan_in
    assert all(
        note.startswith("near_budget:") or note.startswith("at_budget:")
        for note in baseline["budget_review_notes"]
    )
