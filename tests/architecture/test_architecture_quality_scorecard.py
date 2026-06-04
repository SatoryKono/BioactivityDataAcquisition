"""Architecture guardrail for committed architecture quality scorecard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bioetl.infrastructure.quality.architecture_quality_scorecard import (
    build_architecture_quality_scorecard,
)

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "reports" / "quality" / "architecture-quality-scorecard.json"

pytestmark = pytest.mark.architecture


def test_architecture_quality_scorecard_artifact_matches_live_collector() -> None:
    assert ARTIFACT.exists()

    committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    live = build_architecture_quality_scorecard(repo_root=ROOT)

    assert committed == live


def test_architecture_quality_scorecard_blocks_debt_budget_growth_policy() -> None:
    committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert committed["weights_sum"] == 1.0
    assert committed["debt_budget_policy"]["budget_growth_allowed"] is False
    assert len(committed["categories"]) == 10
