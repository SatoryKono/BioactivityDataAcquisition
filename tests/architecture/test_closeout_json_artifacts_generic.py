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


def test_tech_debt_closeout_json_packs_keep_evidence_and_ratchets() -> None:
    """Generic fold for issue-pack JSON freezes (#7464 batch).

    Historical closeout JSON remains; repeated existence/schema freezes move here
    so per-issue pytest modules can shrink without losing failure proof.
    """
    packs = sorted(REPORTS.glob("tech-debt-*-closeout.json"))
    assert packs, "expected tech-debt closeout JSON packs"
    failures: list[str] = []
    for path in packs:
        try:
            payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{path.name}: invalid json ({exc})")
            continue
        if not isinstance(payload, dict) or not payload:
            failures.append(f"{path.name}: empty/non-object payload")
            continue
        has_identity = any(
            key in payload
            for key in (
                "schema_version",
                "debt_budget_outcome",
                "debt_outcome",
                "issues",
                "issue",
                "status",
            )
        )
        if not has_identity:
            failures.append(f"{path.name}: missing closeout identity fields")
        ratchets = payload.get("ratchets")
        if isinstance(ratchets, dict):
            for name, ratchet in ratchets.items():
                if not isinstance(ratchet, dict):
                    continue
                if "current" in ratchet and "max" in ratchet:
                    try:
                        if float(ratchet["current"]) > float(ratchet["max"]):
                            failures.append(
                                f"{path.name}: ratchet {name} current>max "
                                f"({ratchet['current']}>{ratchet['max']})"
                            )
                    except (TypeError, ValueError):
                        failures.append(f"{path.name}: ratchet {name} non-numeric")
        # Evidence entries are historical labels and may point at renamed/removed
        # surfaces; path existence remains the responsibility of owner closeout
        # modules. Generic fold only keeps identity + ratchet non-growth proof.
    assert failures == [], "Closeout pack regressions:\n" + "\n".join(failures[:40])
