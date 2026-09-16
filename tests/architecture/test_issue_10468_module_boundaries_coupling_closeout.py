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
"""Closeout guards for #10468/#10475 module-boundaries coupling 10.0."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.infrastructure.quality.architecture_quality_scoring import (
    _score_module_boundaries_coupling,
)
from scripts.engineering.qa.hotspot_family_metrics import collect_hotspot_family_metrics
from scripts.engineering.qa.report_hotspot_family_baseline import (
    _budget_review_notes_for_family,
    _budget_warnings_for_family,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SCORECARD = ROOT / "reports" / "quality" / "architecture-quality-scorecard.json"
HOTSPOT_BASELINE = ROOT / "reports" / "quality" / "hotspot-family-baseline.json"
DEBT_SCORECARD = ROOT / "configs" / "quality" / "debt_scorecard.yaml"

CONTROL_PLANE = "application_services_control_plane"
RUNTIME_BUILDERS = "composition_runtime_builders"
CONTROL_PLANE_FAN_IN_CAP = 2
RUNTIME_BUILDERS_FAN_IN_CAP = 3


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _hotspot_family(payload: dict[str, Any], name: str) -> dict[str, Any]:
    for family in payload["families"]:
        if family["name"] == name:
            return family
    raise AssertionError(f"missing hotspot family: {name}")


def _debt_family(payload: dict[str, Any], name: str) -> dict[str, Any]:
    for family in payload["hotspot_family_ratchets"]["families"]:
        if family["name"] == name:
            return family
    raise AssertionError(f"missing debt-scorecard family: {name}")


def _category(payload: dict[str, Any], category_id: str) -> dict[str, Any]:
    for category in payload["categories"]:
        if category["id"] == category_id:
            return category
    raise AssertionError(f"missing scorecard category: {category_id}")


def _live_families() -> dict[str, dict[str, Any]]:
    return {family.name: family.to_dict() for family in collect_hotspot_family_metrics()}


def test_issue_10468_generated_scorecard_proves_coupling_10() -> None:
    """#10475: coupling 10.0 is derived from generated metrics, not a hardcoded grade."""
    scorecard = _load_json(SCORECARD)
    hotspot = _load_json(HOTSPOT_BASELINE)
    metrics = scorecard["metrics"]
    diagnostics = scorecard["diagnostics"]
    category = _category(scorecard, "module_boundaries_coupling")

    derived = _score_module_boundaries_coupling(metrics)
    assert derived == 10.0
    assert category["score"] == derived
    assert metrics["families_at_budget_count"] == 0
    assert diagnostics["families_at_budget_count"] == 0
    assert diagnostics["families_at_budget"] == []
    assert metrics["hotspot_budget_warning_count"] == 0
    assert hotspot["summary"]["budget_warnings"] == 0
    assert metrics["total_duplicate_clusters"] == 0
    assert metrics["layer_violations"] == 0
    assert diagnostics["lazy_import_observed_count"] == 0
    assert diagnostics["lazy_import_cap"] == 0
    assert diagnostics["lazy_util"] == 0.0
    assert metrics["lazy_import_observed_count"] == 0
    assert metrics["lazy_import_cap"] == 0
    assert metrics["lazy_util"] == 0.0


def test_issue_10468_hotspot_family_maxima_and_caps_hold() -> None:
    """C2–C4 maxima stay below shrink-only caps; C5 evidence matches live census."""
    hotspot = _load_json(HOTSPOT_BASELINE)
    debt = _load_yaml(DEBT_SCORECARD)
    live = _live_families()

    control_plane = _hotspot_family(hotspot, CONTROL_PLANE)
    builders = _hotspot_family(hotspot, RUNTIME_BUILDERS)
    debt_control_plane = _debt_family(debt, CONTROL_PLANE)
    debt_builders = _debt_family(debt, RUNTIME_BUILDERS)
    live_control_plane = live[CONTROL_PLANE]
    live_builders = live[RUNTIME_BUILDERS]

    assert control_plane["bounded_growth_budgets"]["max_internal_fan_in"] == (
        CONTROL_PLANE_FAN_IN_CAP
    )
    assert builders["bounded_growth_budgets"]["max_internal_fan_in"] == (
        RUNTIME_BUILDERS_FAN_IN_CAP
    )
    assert debt_control_plane["bounded_growth_budgets"]["max_internal_fan_in"] == (
        CONTROL_PLANE_FAN_IN_CAP
    )
    assert debt_builders["bounded_growth_budgets"]["max_internal_fan_in"] == (
        RUNTIME_BUILDERS_FAN_IN_CAP
    )
    assert control_plane["bounded_growth_budgets"]["files_ge_250_loc"] == 0
    assert builders["bounded_growth_budgets"]["files_ge_250_loc"] == 0

    assert live_control_plane["max_internal_fan_in"] <= 1
    assert live_builders["max_internal_fan_in"] <= 2
    assert live_control_plane["files_ge_250_loc"] == 0
    assert live_builders["files_ge_250_loc"] == 0

    assert control_plane["max_internal_fan_in"] == live_control_plane["max_internal_fan_in"]
    assert builders["max_internal_fan_in"] == live_builders["max_internal_fan_in"]
    assert control_plane["files"] == live_control_plane["files"]
    assert builders["files"] == live_builders["files"]
    assert control_plane["files_ge_250_loc"] == 0
    assert builders["files_ge_250_loc"] == 0

    assert debt_control_plane["metrics"]["max_internal_fan_in"] == (
        live_control_plane["max_internal_fan_in"]
    )
    assert debt_builders["metrics"]["max_internal_fan_in"] == (
        live_builders["max_internal_fan_in"]
    )
    assert debt_control_plane["metrics"]["files"] == live_control_plane["files"]
    assert debt_builders["metrics"]["files"] == live_builders["files"]

    for family in (control_plane, builders, live_control_plane, live_builders):
        assert _budget_warnings_for_family(family) == []
        assert not any(
            note.startswith("at_budget:")
            for note in _budget_review_notes_for_family(family)
        )
