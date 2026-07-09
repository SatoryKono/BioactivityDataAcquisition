"""Architecture guardrails for zero-reference supporting-script governance."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCORECARD_PATH = PROJECT_ROOT / "configs/quality/debt_scorecard.yaml"
MANIFEST_PATH = PROJECT_ROOT / "configs/quality/scripts_inventory_manifest.json"


def _load_yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_zero_reference_supporting_scripts_are_triaged_and_ratcheted() -> None:
    """Zero-reference supporting scripts must stay triaged within scorecard budgets."""
    if sys.platform.startswith("win"):
        pytest.skip("Scripts inventory governance check requires full repo walk which is prohibitively slow on Windows")
    scorecard = _load_yaml(SCORECARD_PATH)
    policy = scorecard.get("supporting_scripts_governance", {})
    assert isinstance(policy, dict)
    metrics = policy.get("metrics", {})
    assert isinstance(metrics, dict)

    zero_ref_budget = metrics.get("zero_reference_supporting_script_count", {})
    untriaged_budget = metrics.get(
        "untriaged_zero_reference_supporting_script_count", {}
    )
    assert isinstance(zero_ref_budget, dict)
    assert isinstance(untriaged_budget, dict)

    manifest = _load_json(MANIFEST_PATH)
    scripts = manifest.get("scripts", [])
    assert isinstance(scripts, list)
    zero_ref_rows = [row for row in scripts if row.get("reference_count") == 0]

    assert len(zero_ref_rows) <= int(zero_ref_budget["max_count"])
    missing_metadata = [
        row["path"]
        for row in zero_ref_rows
        if not row.get("owner")
        or not row.get("lifecycle_decision")
        or not row.get("review_by")
        or not row.get("next_step")
    ]
    assert len(missing_metadata) <= int(untriaged_budget["max_count"])
