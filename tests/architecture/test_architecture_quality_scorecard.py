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


def test_architecture_quality_scorecard_includes_adr_and_observability_gates() -> None:
    committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert committed["source_artifacts"]["adr_enforcement_matrix"]["path"] == (
        "reports/quality/adr-enforcement-matrix.json"
    )
    assert committed["source_artifacts"][
        "observability_runtime_cardinality_inventory"
    ]["path"] == "reports/observability/runtime_cardinality_inventory.json"
    assert committed["metrics"]["adr_enforcement_blocking_gap_count"] == 0
    assert committed["metrics"]["dashboarded_without_emission_count"] == 0
    assert committed["metrics"]["dashboarded_without_declaration_count"] == 0
    assert committed["metrics"]["runtime_cardinality_review_required_count"] == 0
