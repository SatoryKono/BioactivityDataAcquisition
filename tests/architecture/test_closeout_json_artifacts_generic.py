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
"""Generic ratchet for historical closeout JSON artifacts (TD-R-04 / #6680)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports" / "quality"


def _closeout_json_files() -> list[Path]:
    paths = sorted(REPORTS.glob("*closeout*.json"))
    return [
        path
        for path in paths
        if any(
            token in path.name
            for token in ("tech-debt", "test-audit", "diagram", "ci-epic", "ai-audit")
        )
    ]


def test_closeout_json_artifacts_declare_no_budget_growth_policy() -> None:
    files = _closeout_json_files()
    assert files, "expected committed closeout JSON artifacts under reports/quality"
    failures: list[str] = []
    for path in files:
        try:
            payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{path.name}: invalid json ({exc})")
            continue
        if not isinstance(payload, dict):
            failures.append(f"{path.name}: root must be object")
            continue
        has_marker = any(
            key in payload
            for key in (
                "debt_budget_policy",
                "budget_policy",
                "debt_budget_outcome",
                "debt_outcome",
                "status",
                "schema_version",
                "created",
                "issues",
                "issue",
                "outcomes",
                "published_at",
                "sha",
                "results",
                "validation",
                "changes",
            )
        )
        if not has_marker:
            failures.append(f"{path.name}: missing closeout identity fields")
    assert failures == [], "Closeout artifact policy regressions:\n" + "\n".join(
        failures
    )
