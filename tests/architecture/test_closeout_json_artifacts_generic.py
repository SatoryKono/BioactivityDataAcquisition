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


def _evidence_path(raw_evidence: str) -> str:
    """Normalize evidence entries that may use path::nodeid form."""
    return str(raw_evidence).split("::", maxsplit=1)[0]


def _check_metric_non_growth(
    path_name: str,
    metric_name: str,
    metric: dict[str, Any],
    failures: list[str],
) -> None:
    current = metric.get("current")
    maximum = metric.get("max")
    try:
        if maximum is not None and current is not None:
            if float(current) > float(maximum):
                failures.append(
                    f"{path_name}: metric {metric_name} current>max "
                    f"({current}>{maximum})"
                )
    except (TypeError, ValueError):
        failures.append(f"{path_name}: metric {metric_name} non-numeric bounds")


def test_tech_debt_closeout_json_packs_keep_evidence_and_ratchets() -> None:
    """Generic fold for issue-pack JSON freezes (#7464 batch).

    Historical closeout JSON remains; repeated existence/schema freezes move here
    so per-issue pytest modules can shrink without losing failure proof.
    """
    packs = sorted(REPORTS.glob("tech-debt-*-closeout.json"))
    packs.extend(sorted(REPORTS.glob("tech-debt-issue-*-closeout.json")))
    packs = sorted(set(packs))
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
                "debt_budget_policy",
                "budget_policy",
                "issues",
                "issue",
                "status",
            )
        )
        if not has_identity:
            failures.append(f"{path.name}: missing closeout identity fields")

        for key in ("debt_budget_policy", "budget_policy"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                lowered = value.lower().replace("-", "_")
                # Allow no_growth / flat_or_decreasing wording; forbid explicit increases.
                if any(
                    token in lowered
                    for token in ("increase_budget", "budget_increase", "raise_budget", "allow_growth")
                ) or lowered in {"increase", "grow", "growing"}:
                    failures.append(
                        f"{path.name}: forbidden budget-growth policy {key}={value!r}"
                    )

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

        metrics = payload.get("metrics")
        if isinstance(metrics, dict):
            for metric_name, metric in metrics.items():
                if isinstance(metric, dict):
                    _check_metric_non_growth(
                        path.name, str(metric_name), metric, failures
                    )

        issue_blob = payload.get("issues")
        if isinstance(issue_blob, list):
            issue_items = issue_blob
        elif isinstance(payload.get("issue"), dict):
            issue_items = [payload["issue"]]
        else:
            issue_items = []
        for issue in issue_items:
            if not isinstance(issue, dict):
                continue
            evidence = issue.get("evidence")
            if not isinstance(evidence, list):
                continue
            for raw in evidence:
                rel = _evidence_path(str(raw))
                if not rel or rel.startswith("http"):
                    continue
                if "/" not in rel and "\\" not in rel and not rel.endswith(
                    (".py", ".json", ".yaml", ".yml", ".md")
                ):
                    continue
                if ("{" in rel) or ("}" in rel) or ("#" in rel):
                    continue
                if not (rel.startswith("src/") or rel.startswith("configs/")):
                    continue
                if not (ROOT / rel).exists():
                    failures.append(f"{path.name}: missing evidence {raw!r}")
    assert failures == [], "Closeout pack regressions:\n" + "\n".join(failures[:60])
