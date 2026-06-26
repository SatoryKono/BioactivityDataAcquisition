"""Architecture guardrail for committed architecture quality scorecard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "reports" / "quality" / "architecture-quality-scorecard.json"
MODULE_COVERAGE_ARTIFACT = (
    ROOT / "reports" / "quality" / "module-coverage-inventory.json"
)
DUPLICATION_BASELINE_ARTIFACT = (
    ROOT / "reports" / "quality" / "full-app-duplication-baseline.json"
)
HOTSPOT_BASELINE_ARTIFACT = ROOT / "reports" / "quality" / "hotspot-family-baseline.json"
TEST_GOVERNANCE_ARTIFACT = ROOT / "reports" / "quality" / "test-governance-current.json"


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
def test_architecture_quality_scorecard_module_coverage_evidence_is_consistent() -> (
    None
):
    """Scorecard module counts and hashes must match the canonical coverage artifact."""
    committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    coverage_inventory = json.loads(
        MODULE_COVERAGE_ARTIFACT.read_text(encoding="utf-8")
    )
    inventory_summary = coverage_inventory["summary"]

    source_artifact = committed["source_artifacts"]["module_coverage_inventory"]
    assert source_artifact["path"] == "reports/quality/module-coverage-inventory.json"
    assert (
        source_artifact["source_tree_sha256"]
        == coverage_inventory["source_tree_sha256"]
    )
    assert (
        source_artifact["coverage_xml_sha256"]
        == coverage_inventory["coverage_xml_sha256"]
    )

    assert (
        committed["metrics"]["source_module_count"]
        == inventory_summary["source_module_count"]
    )
    assert (
        committed["metrics"]["unmeasured_module_count"]
        == inventory_summary["unmeasured_module_count"]
    )
    assert (
        committed["metrics"]["uncovered_module_count"]
        == inventory_summary["uncovered_module_count"]
    )

    for category in committed["categories"]:
        evidence_metrics = category.get("evidence_metrics", {})
        if "source_module_count" in evidence_metrics:
            assert (
                evidence_metrics["source_module_count"]
                == inventory_summary["source_module_count"]
            )
        if "unmeasured_module_count" in evidence_metrics:
            assert (
                evidence_metrics["unmeasured_module_count"]
                == inventory_summary["unmeasured_module_count"]
            )
        if "uncovered_module_count" in evidence_metrics:
            assert (
                evidence_metrics["uncovered_module_count"]
                == inventory_summary["uncovered_module_count"]
            )


@pytest.mark.architecture
def test_architecture_quality_scorecard_includes_adr_and_observability_gates() -> None:
    committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert committed["source_artifacts"]["adr_enforcement_matrix"]["path"] == (
        "scripts/engineering/qa/report_adr_enforcement_matrix.py::build_payload"
    )
    assert (
        committed["source_artifacts"]["adr_enforcement_matrix"]["generated_artifact"]
        == "reports/quality/adr-enforcement-matrix.json"
    )
    assert committed["source_artifacts"]["contract_registry_dq_diagnostics"][
        "path"
    ] == (
        "scripts/engineering/ci/validate_registry_dq_refs.py::build_diagnostics_payload"
    )
    assert (
        committed["source_artifacts"]["observability_runtime_cardinality_inventory"][
            "path"
        ]
        == "reports/observability/runtime_cardinality_inventory.json"
    )
    assert committed["metrics"]["adr_enforcement_blocking_gap_count"] == 0
    assert committed["metrics"]["dashboarded_without_emission_count"] == 0
    assert committed["metrics"]["dashboarded_without_declaration_count"] == 0
    assert committed["metrics"]["runtime_cardinality_review_required_count"] == 0


@pytest.mark.architecture
def test_architecture_quality_scorecard_includes_duplication_hotspot_and_test_governance_evidence() -> (
    None
):
    committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    duplication = json.loads(DUPLICATION_BASELINE_ARTIFACT.read_text(encoding="utf-8"))
    hotspot = json.loads(HOTSPOT_BASELINE_ARTIFACT.read_text(encoding="utf-8"))
    test_governance = json.loads(TEST_GOVERNANCE_ARTIFACT.read_text(encoding="utf-8"))

    duplication_artifact = committed["source_artifacts"]["duplication_baseline"]
    assert duplication_artifact["path"] == "reports/quality/full-app-duplication-baseline.json"
    assert duplication_artifact["snapshot_date"] == duplication["summary"]["snapshot_date"]
    assert (
        duplication_artifact["total_duplicate_clusters"]
        == duplication["summary"]["total_duplicate_clusters"]
    )

    hotspot_artifact = committed["source_artifacts"]["hotspot_family_baseline"]
    assert hotspot_artifact["path"] == "reports/quality/hotspot-family-baseline.json"
    assert hotspot_artifact["snapshot_date"] == hotspot["summary"]["snapshot_date"]
    assert hotspot_artifact["budget_warnings"] == hotspot["summary"]["budget_warnings"]

    governance_artifact = committed["source_artifacts"]["test_governance_report"]
    assert governance_artifact["path"] == "reports/quality/test-governance-current.json"
    assert (
        governance_artifact["compatibility_test_files"]
        == test_governance["report"]["compatibility_test_files"]
    )

    assert (
        committed["metrics"]["total_duplicate_clusters"]
        == duplication["summary"]["total_duplicate_clusters"]
    )
    assert (
        committed["metrics"]["hotspot_budget_warning_count"]
        == hotspot["summary"]["budget_warnings"]
    )
    assert (
        committed["metrics"]["compatibility_test_file_count"]
        == test_governance["report"]["compatibility_test_files"]
    )
