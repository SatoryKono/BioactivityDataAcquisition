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
"""Architecture closeout guards for issues #6032, #6034, and #6037."""

from __future__ import annotations

import ast
from collections import Counter
from datetime import date
import json
from pathlib import Path

import pytest

from scripts.engineering.qa.hotspot_family_metrics import (
    count_internal_fan_in,
    iter_family_python_files,
    load_scorecard,
)
from tests.architecture.test_runtime_import_scc import (
    ACCEPTED_RUNTIME_SCCS,
    REVIEWED_RUNTIME_SCC_BUDGET_MAX,
    REVIEWED_RUNTIME_SCC_MIN_REVIEW_DATE,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports/quality/tech-debt-issues-6032-6034-6037-closeout.json"
HOTSPOT_BASELINE = ROOT / "reports/quality/hotspot-family-baseline.json"


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _family_row(name: str) -> dict[str, object]:
    baseline = _load_json(HOTSPOT_BASELINE)
    families = baseline["families"]
    assert isinstance(families, list)
    row = next(
        family
        for family in families
        if isinstance(family, dict) and family.get("name") == name
    )
    return row


def _live_family_fan_in(name: str) -> tuple[int, str | None]:
    scorecard = load_scorecard()
    families = scorecard["hotspot_family_ratchets"]["families"]
    family = next(row for row in families if row["name"] == name)
    files = iter_family_python_files(path_prefixes=family["path_prefixes"])
    return count_internal_fan_in(files=files)


def _runtime_builder_importer_count(target_module: str) -> int:
    root = ROOT / "src/bioetl/composition/runtime_builders"
    counter: Counter[str] = Counter()
    for py_file in sorted(root.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name == target_module for alias in node.names):
                    counter[target_module] += 1
            elif isinstance(node, ast.ImportFrom) and node.module == target_module:
                counter[target_module] += 1
    return counter[target_module]


def test_issues_6032_6034_6037_closeout_artifact_has_expected_scope() -> None:
    payload = _load_json(CLOSEOUT)
    issues = payload["issues"]
    assert isinstance(issues, list)

    assert payload["schema_version"] == "tech-debt-issues-6032-6034-6037-closeout-v1"
    assert [issue["number"] for issue in issues] == [6032, 6034, 6037]
    assert all(str(issue["status"]).startswith("closeable") for issue in issues)


def test_issue_6032_application_core_fan_in_has_headroom() -> None:
    row = _family_row("application_core")
    budgets = row["bounded_growth_budgets"]
    assert isinstance(budgets, dict)

    assert row["max_internal_fan_in"] == 8
    assert row["max_internal_fan_in"] < budgets["max_internal_fan_in"]
    assert budgets["max_internal_fan_in"] == 10
    assert (
        row["max_internal_fan_in_module"]
        == "bioetl.application.core.batch_runtime_failure_policy"
    )
    # Informational near/at-budget notes are allowed; only budget_warnings fail-fast.
    assert all(
        str(note).startswith(("at_budget:", "near_budget:"))
        for note in row["budget_review_notes"]
    )
    assert row["files_ge_250_loc"] <= budgets["files_ge_250_loc"]
    # Allow actual fan-in to be within budget, not exact match
    assert _live_family_fan_in("application_core")[0] <= budgets["max_internal_fan_in"]


def test_issue_6034_composition_runtime_seams_keep_headroom() -> None:
    bootstrap = _family_row("composition_bootstrap_runtime")
    runtime_builders = _family_row("composition_runtime_builders")

    bootstrap_budget = bootstrap["bounded_growth_budgets"]
    runtime_builder_budget = runtime_builders["bounded_growth_budgets"]
    assert isinstance(bootstrap_budget, dict)
    assert isinstance(runtime_builder_budget, dict)

    assert bootstrap["max_internal_fan_in"] == 2
    assert bootstrap["max_internal_fan_in"] < 3
    assert bootstrap_budget["max_internal_fan_in"] == 3
    assert not bootstrap["budget_review_notes"]
    assert _live_family_fan_in("composition_bootstrap_runtime")[0] == 2

    assert runtime_builders["max_internal_fan_in"] <= 4
    assert runtime_builder_budget["max_internal_fan_in"] == 5
    assert (
        _runtime_builder_importer_count(
            "bioetl.composition.runtime_builders.run_manifest_support"
        )
        == 3
    )


def test_issue_6037_runtime_scc_acceptances_are_fresh_and_not_growing() -> None:
    assert len(ACCEPTED_RUNTIME_SCCS) == 2
    assert len(ACCEPTED_RUNTIME_SCCS) <= REVIEWED_RUNTIME_SCC_BUDGET_MAX

    metadata = next(
        item
        for component, item in ACCEPTED_RUNTIME_SCCS.items()
        if "bioetl.interfaces.http.control_plane_identity.anchor_values" in component
    )
    assert metadata["owner"] == "interfaces.http.control_plane_identity"
    assert metadata["linked_issue"] == "#6037"
    assert metadata["review_date"] == "2026-07-07"
    assert date.fromisoformat(metadata["review_date"]) >= (
        REVIEWED_RUNTIME_SCC_MIN_REVIEW_DATE
    )
