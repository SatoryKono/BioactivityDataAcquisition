"""Architecture guardrail for committed architecture quality scorecard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "reports" / "quality" / "architecture-quality-scorecard.json"


def _normalize_live_collector_comparison(
    payload: dict[str, object],
) -> dict[str, object]:
    """Drop module-coverage-derived evidence handled by dedicated inventory tests."""
    normalized = json.loads(json.dumps(payload))
    source_artifacts = normalized.get("source_artifacts")
    if isinstance(source_artifacts, dict):
        module_coverage_inventory = source_artifacts.get("module_coverage_inventory")
        if isinstance(module_coverage_inventory, dict):
            module_coverage_inventory.pop("source_tree_sha256", None)
            module_coverage_inventory.pop("coverage_xml_sha256", None)

    metrics = normalized.get("metrics")
    if isinstance(metrics, dict):
        metrics.pop("source_module_count", None)
        metrics.pop("unmeasured_module_count", None)
        metrics.pop("uncovered_module_count", None)

    categories = normalized.get("categories")
    if isinstance(categories, list):
        for category in categories:
            if not isinstance(category, dict):
                continue
            evidence_metrics = category.get("evidence_metrics")
            if not isinstance(evidence_metrics, dict):
                continue
            evidence_metrics.pop("source_module_count", None)
            evidence_metrics.pop("unmeasured_module_count", None)
            evidence_metrics.pop("uncovered_module_count", None)

    return normalized


@pytest.mark.architecture
def test_architecture_quality_scorecard_artifact_matches_live_collector() -> None:
    assert ARTIFACT.exists()

    committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    from bioetl.infrastructure.quality.architecture_quality_scorecard import (
        build_architecture_quality_scorecard,
    )
    live = build_architecture_quality_scorecard(repo_root=ROOT)

    assert _normalize_live_collector_comparison(committed) == (
        _normalize_live_collector_comparison(live)
    )


@pytest.mark.architecture
def test_architecture_quality_scorecard_blocks_debt_budget_growth_policy() -> None:
    committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert committed["weights_sum"] == 1.0
    assert committed["debt_budget_policy"]["budget_growth_allowed"] is False
    assert len(committed["categories"]) == 10


@pytest.mark.architecture
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
