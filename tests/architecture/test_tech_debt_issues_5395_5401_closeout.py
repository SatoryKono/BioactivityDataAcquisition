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
"""Closeout guardrails for technical-debt issues #5395-#5401."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5395-5401-closeout.json"
HOTSPOT_BASELINE = ROOT / "reports" / "quality" / "hotspot-family-baseline.json"
LAYER_MATRIX = ROOT / "reports" / "quality" / "layer-contract-coverage-matrix.json"
TIME_SEAMS = ROOT / "configs" / "quality" / "time_seam_classification.yaml"
EXPECTED_ISSUES = {5395, 5396, 5397, 5398, 5399, 5400, 5401}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def _evidence_path(raw: str) -> str:
    return raw.split("::", maxsplit=1)[0].split("#", maxsplit=1)[0]


def test_issue_5395_time_seams_are_classified_without_replay_exceptions() -> None:
    payload = yaml.safe_load(TIME_SEAMS.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    seams = cast(list[dict[str, Any]], payload["seams"])

    categories = {str(seam["category"]) for seam in seams}
    assert "operator_time_allowed" in categories
    assert "runtime_clock_adapter" in categories
    assert all(seam["category"] != "replay_time_forbidden" for seam in seams)
    assert all(seam["replay_critical"] is False for seam in seams)


def test_issue_5398_layer_matrix_has_bronze_silver_gold_rows() -> None:
    payload = _load_json(LAYER_MATRIX)
    rows = cast(list[dict[str, Any]], payload["rows"])
    layers_by_pipeline: dict[str, set[str]] = {}
    for row in rows:
        layers_by_pipeline.setdefault(str(row["pipeline_name"]), set()).add(
            str(row["dataset_layer"])
        )

    assert payload["summary"]["layers"] == ["bronze", "silver", "gold"]
    assert all(
        layers == {"bronze", "silver", "gold"} for layers in layers_by_pipeline.values()
    )
    assert payload["summary"]["coverage_levels"]["strict"] > 0
    assert payload["summary"]["coverage_levels"]["moderate"] > 0
    assert payload["summary"]["coverage_levels"]["structural_only"] > 0


def test_issue_5400_hotspot_family_budget_warnings_are_reviewed_budget_closures() -> (
    None
):
    hotspot = _load_json(HOTSPOT_BASELINE)
    families = cast(list[dict[str, Any]], hotspot["families"])

    assert hotspot["summary"]["budget_warnings"] == 0
    assert hotspot["summary"]["budget_review_notes"] == sum(
        len(family["budget_review_notes"]) for family in families
    )
    for family in families:
        assert all(
            str(warning).startswith("over_budget:")
            for warning in family["budget_warnings"]
        )
        assert all(
            str(note).startswith(("at_budget:", "near_budget:"))
            for note in family["budget_review_notes"]
        )
        budgets = cast(dict[str, int], family["bounded_growth_budgets"])
        assert int(family["files_ge_250_loc"]) <= budgets["files_ge_250_loc"]
        assert int(family["max_internal_fan_in"]) <= budgets["max_internal_fan_in"]


def test_issue_5401_architecture_governance_mirror_points_to_machine_evidence() -> None:
    doc = (
        ROOT / "docs" / "02-architecture" / "governance-audit-evidence.md"
    ).read_text(encoding="utf-8")

    assert "does not redefine runtime behavior" in doc
    assert "reports/quality/architecture-quality-scorecard.json" in doc
    assert "reports/quality/hotspot-family-baseline.json" in doc
    assert "reports/quality/layer-contract-coverage-matrix.json" in doc
