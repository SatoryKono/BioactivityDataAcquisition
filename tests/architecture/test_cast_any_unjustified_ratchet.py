# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface - product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Shrink-only ratchet for unjustified ``cast(Any, ...)`` call sites (#10596)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.engineering.qa.report_cast_any_typing_census import (
    build_cast_any_census,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
BUDGET = ROOT / "configs" / "quality" / "cast_any_unjustified_budget.yaml"


def _load_budget() -> dict[str, Any]:
    payload = yaml.safe_load(BUDGET.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def live_census() -> dict[str, Any]:
    return build_cast_any_census(ROOT)


def test_cast_any_unjustified_count_stays_within_shrink_only_budget(
    live_census: dict[str, Any],
) -> None:
    budget = _load_budget()
    assert budget["ratchet_policy"] == "shrink_only"
    max_unjustified = int(budget["max_unjustified_count"])
    unjustified = int(live_census["summary"]["unjustified_count"])
    top_unjustified = [
        f"{row['path']} ({row['unjustified']})"
        for row in live_census["top_files"]
        if int(row["unjustified"]) > 0
    ][:15]
    assert unjustified <= max_unjustified, (
        f"unjustified cast(Any) count {unjustified} exceeds shrink-only budget "
        f"{max_unjustified} (configs/quality/cast_any_unjustified_budget.yaml). "
        "Replace host-default casts with Protocol host surfaces or add a reviewed "
        "PD3/PD6/TYPE-002 justification instead of raising the budget.\n"
        "Top files:\n" + "\n".join(f"  - {item}" for item in top_unjustified)
    )


def test_cast_any_budget_never_exceeds_recorded_baseline() -> None:
    """The budget file itself must not drift above its own recorded baseline."""
    budget = _load_budget()
    baseline = budget["baseline"]
    assert int(budget["max_unjustified_count"]) <= int(baseline["unjustified_count"])
    assert int(baseline["unjustified_count"]) <= 142
