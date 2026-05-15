<<<<<<< Updated upstream
"""Contract checks for semantic pair-matrix drift budgets."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import yaml

from scripts.engineering.qa.check_semantic_pair_matrix_budget import (
    DEFAULT_BUDGET_PATH,
    validate_semantic_pair_matrix_budget,
)
from scripts.engineering.qa.check_semantic_registry_drift import (
    validate_semantic_registry_drift,
)


def test_semantic_pair_matrix_budget_gate_passes_current_repo() -> None:
    result = validate_semantic_pair_matrix_budget(
        repo_root=Path("."),
        today=date(2026, 5, 15),
    )

    assert not result.findings, "\n".join(
        finding.message for finding in result.findings
    )


def test_pair_matrix_budget_records_current_risk_counts() -> None:
    result = validate_semantic_pair_matrix_budget(
        repo_root=Path("."),
        today=date(2026, 5, 15),
    )

    assert result.risk_counts.get("CRITICAL", 0) == 0
    assert result.risk_counts.get("HIGH", 0) == 0
    assert result.risk_counts.get("MEDIUM", 0) == 0


def test_reviewed_critical_rows_are_timeboxed_and_owned() -> None:
    payload = yaml.safe_load(DEFAULT_BUDGET_PATH.read_text(encoding="utf-8"))
    reviewed_rows = payload["reviewed_critical_rows"]

    assert payload["matrix_path"].endswith("semantic_pair_matrix_2026-05-15.csv")
    assert payload["review_registry_path"].endswith(
        "semantic_audit_review_registry.yaml"
    )
    assert payload["reviewed_on"] == "2026-05-15"
    assert {
        (row["column"], row["value"]): row["max_count"]
        for row in payload["status_budgets"]
    } == {
        ("Semantic Status", "PARTIAL"): 67,
        ("Semantic Status", "WEAK"): 439,
        ("Semantic Status", "CONFLICTING"): 20,
        ("Normalization", "DIFFERENT"): 0,
        ("Normalization", "COMPATIBLE"): 900,
        ("Typing", "CONFLICTING"): 0,
        ("Typing", "COMPATIBLE"): 664,
        ("Validation", "STRICTNESS_MISMATCH"): 0,
        ("Validation", "COMPATIBLE"): 1053,
    }
    assert len(reviewed_rows) == payload["budgets"]["CRITICAL"]["max_count"]
    for row in reviewed_rows:
        assert row["row_key"]
        assert row["owner"] == "BioETL Team"
        assert row["expires_on"]
        assert row["rationale"]


def test_semantic_audit_manifest_tracks_base_config_coverage() -> None:
    manifest_path = Path(
        "reports/semantic_pipeline_audit/semantic_pipeline_audit_manifest_2026-05-15.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    base_configs = payload["counts"]["base_configs"]
    artifact_name = payload["artifacts"]["base_config_semantic_coverage"]
    coverage_path = Path("reports/semantic_pipeline_audit") / artifact_name
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))

    expected_paths = {
        "configs/base/bronze_fixture_gaps.yaml",
        "configs/base/bronze_fixture_manifest.yaml",
        "configs/base/contract_registry.yaml",
        "configs/base/pipeline.yaml",
        "configs/base/quality.yaml",
    }
    actual_paths = {entry["path"] for entry in coverage["entries"]}

    assert base_configs["base_config_count"] == len(expected_paths)
    assert base_configs["semantic_surface_count"] > 0
    assert actual_paths == expected_paths
    assert coverage == base_configs


def test_semantic_audit_manifest_tracks_residual_backlog() -> None:
    manifest_path = Path(
        "reports/semantic_pipeline_audit/semantic_pipeline_audit_manifest_2026-05-15.json"
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact_name = payload["artifacts"]["residual_backlog"]
    backlog_path = Path("reports/semantic_pipeline_audit") / artifact_name
    markdown_name = payload["artifacts"]["residual_backlog_markdown"]
    markdown_path = Path("reports/semantic_pipeline_audit") / markdown_name
    backlog = json.loads(backlog_path.read_text(encoding="utf-8"))

    assert payload["artifact_count"] == 8
    assert backlog["summary"] == payload["counts"]["residual_backlog"]
    assert backlog["summary"]["blocking_task_count"] == 0
    assert {task["id"] for task in backlog["tasks"]} >= {
        "semantic_drift_budget",
        "hard_status_mismatch_budget",
        "partial_identity_policy_review",
        "weak_same_name_inventory_review",
        "generic_collision_inventory_review",
        "compatible_normalization_ratchet",
        "compatible_validation_ratchet",
        "compatible_typing_ratchet",
        "base_config_semantic_coverage",
    }
    assert markdown_path.exists()


def test_non_exact_semantic_clusters_are_owner_reviewed() -> None:
    registry_path = Path(
        "reports/semantic_pipeline_audit/semantic_cluster_registry_2026-05-15.json"
    )
    payload = json.loads(registry_path.read_text(encoding="utf-8"))

    unreviewed = []
    for cluster in payload["clusters"]:
        if cluster.get("semantic_status") not in {"PARTIAL", "WEAK", "CONFLICTING"}:
            continue
        review = cluster.get("review")
        if not isinstance(review, dict) or not {
            "expires_on",
            "owner",
            "rationale",
            "review_id",
        } <= set(review):
            unreviewed.append(cluster["cluster_id"])

    assert not unreviewed, sorted(unreviewed)[:20]


def test_reviewed_semantic_registry_warnings_are_suppressed() -> None:
    result = validate_semantic_registry_drift(Path("."))

    assert result.ok
    assert result.warnings == ()


def test_generated_cluster_registry_does_not_keep_stale_risk_caps() -> None:
    registry_path = Path(
        "reports/semantic_pipeline_audit/semantic_cluster_registry_2026-05-15.json"
    )
    payload = json.loads(registry_path.read_text(encoding="utf-8"))

    stale = [
        cluster["cluster_id"]
        for cluster in payload["clusters"]
        if isinstance(cluster.get("review"), dict) and cluster["review"].get("risk_cap")
    ]

    assert stale == []


def test_semantic_governance_workflow_runs_blocking_gates() -> None:
    workflow_path = Path(".github/workflows/semantic-governance.yml")
    workflow = workflow_path.read_text(encoding="utf-8")

    for command in (
        "report-semantic-pipeline-audit --check",
        "check-semantic-pair-budget --check --json",
        "check-semantic-registry-drift --check --json",
        "check-semantic-anchor-parity --check --json",
        "check-generic-field-ownership --check --json",
        "check-ontology-unit-semantics --check --json",
        "tests/integration/config/test_semantic_pair_matrix_budget.py",
    ):
        assert command in workflow
||||||| Stash base
=======
"""Contract checks for semantic pair-matrix drift budgets."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from scripts.engineering.qa.check_semantic_pair_matrix_budget import (
    DEFAULT_BUDGET_PATH,
    validate_semantic_pair_matrix_budget,
)


def test_semantic_pair_matrix_budget_gate_passes_current_repo() -> None:
    result = validate_semantic_pair_matrix_budget(
        repo_root=Path("."),
        today=date(2026, 5, 14),
    )

    assert not result.findings, "\n".join(
        finding.message for finding in result.findings
    )


def test_pair_matrix_budget_records_current_critical_and_high_counts() -> None:
    result = validate_semantic_pair_matrix_budget(
        repo_root=Path("."),
        today=date(2026, 5, 14),
    )

    assert result.risk_counts["CRITICAL"] == 16
    assert result.risk_counts["HIGH"] == 333


def test_reviewed_critical_rows_are_timeboxed_and_owned() -> None:
    payload = yaml.safe_load(DEFAULT_BUDGET_PATH.read_text(encoding="utf-8"))
    reviewed_rows = payload["reviewed_critical_rows"]

    assert len(reviewed_rows) == payload["budgets"]["CRITICAL"]["max_count"]
    for row in reviewed_rows:
        assert row["row_key"]
        assert row["owner"] == "BioETL Team"
        assert row["expires_on"]
        assert row["rationale"]
>>>>>>> Stashed changes
