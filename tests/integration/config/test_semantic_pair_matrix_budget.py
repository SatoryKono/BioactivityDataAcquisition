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
"""Contract checks for semantic pair-matrix drift budgets."""

from __future__ import annotations

import pytest

import csv
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

pytestmark = pytest.mark.integration

PAIR_MATRIX_HEADERS = ",".join(
    [
        "Cluster ID",
        "Pipeline A",
        "Field A",
        "Pipeline B",
        "Field B",
        "Semantic Status",
        "Normalization",
        "Validation",
        "Typing",
        "Drift Risk",
        "Join Semantics A",
        "Join Semantics B",
        "Normalizer A",
        "Normalizer B",
        "Validation Evidence A",
        "Validation Evidence B",
        "Type A",
        "Type B",
        "Gold Contract A",
        "Gold Contract B",
        "Evidence A",
        "Evidence B",
        "Row Key",
    ]
)


def test_semantic_pair_matrix_budget_gate_passes_current_repo() -> None:
    result = validate_semantic_pair_matrix_budget(
        repo_root=Path("."),
        today=date(2026, 7, 1),
    )

    assert not result.findings, "\n".join(
        finding.message for finding in result.findings
    )


def test_pair_matrix_budget_records_current_risk_counts() -> None:
    result = validate_semantic_pair_matrix_budget(
        repo_root=Path("."),
        today=date(2026, 7, 1),
    )

    assert result.risk_counts.get("CRITICAL", 0) == 0
    assert result.risk_counts.get("HIGH", 0) == 0
    assert result.risk_counts.get("MEDIUM", 0) == 0


def test_reviewed_critical_rows_are_timeboxed_and_owned() -> None:
    payload = yaml.safe_load(DEFAULT_BUDGET_PATH.read_text(encoding="utf-8"))
    reviewed_rows = payload["reviewed_critical_rows"]

    assert payload["matrix_path"].endswith("semantic_pair_matrix_2026-07-01.csv")
    assert payload["review_registry_path"].endswith(
        "semantic_audit_review_registry.yaml"
    )
    assert payload["reviewed_on"] == "2026-07-01"
    assert {
        (row["column"], row["value"]): row["max_count"]
        for row in payload["status_budgets"]
    } == {
        ("Semantic Status", "PARTIAL"): 68,
        ("Semantic Status", "WEAK"): 435,
        ("Semantic Status", "CONFLICTING"): 0,
        ("Normalization", "DIFFERENT"): 0,
        ("Normalization", "COMPATIBLE"): 887,
        ("Typing", "CONFLICTING"): 0,
        ("Typing", "COMPATIBLE"): 666,
        ("Validation", "STRICTNESS_MISMATCH"): 0,
        ("Validation", "COMPATIBLE"): 1046,
    }
    assert len(reviewed_rows) == payload["budgets"]["CRITICAL"]["max_count"]
    for row in reviewed_rows:
        assert row["row_key"]
        assert row["owner"] == "BioETL Team"
        assert row["expires_on"]
        assert row["rationale"]


def test_semantic_audit_manifest_tracks_base_config_coverage() -> None:
    manifest_path = Path(
        "reports/semantic_pipeline_audit/semantic_pipeline_audit_manifest_2026-07-01.json"
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
        "reports/semantic_pipeline_audit/semantic_pipeline_audit_manifest_2026-07-01.json"
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
        "reports/semantic_pipeline_audit/semantic_cluster_registry_2026-07-01.json"
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


def test_regenerated_snapshot_has_no_unknown_composite_typing_rows() -> None:
    matrix_path = Path(
        "reports/semantic_pipeline_audit/semantic_pair_matrix_2026-07-01.csv"
    )
    rows = validate_semantic_pair_matrix_budget(
        repo_root=Path("."),
        today=date(2026, 7, 1),
    )

    assert rows.ok
    unknown_pairs = set()
    with matrix_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            for side in ("A", "B"):
                if (
                    row[f"Pipeline {side}"].startswith("composite_")
                    and row[f"Type {side}"] == "unknown"
                ):
                    unknown_pairs.add((row[f"Pipeline {side}"], row[f"Field {side}"]))

    assert unknown_pairs == set()


def test_reviewed_semantic_registry_warnings_are_suppressed() -> None:
    result = validate_semantic_registry_drift(Path("."))

    assert result.ok
    assert result.warnings == ()


def test_generated_cluster_registry_does_not_keep_stale_risk_caps() -> None:
    registry_path = Path(
        "reports/semantic_pipeline_audit/semantic_cluster_registry_2026-07-01.json"
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
        "check-semantic-governance-policy --check --json",
        "check-semantic-anchor-parity --check --json",
        "check-generic-field-ownership --check --json",
        "check-ontology-unit-semantics --check --json",
        "tests/integration/config/test_semantic_pair_matrix_budget.py",
        "tests/integration/config/test_semantic_governance_policy.py",
    ):
        assert command in workflow


def test_current_registry_keeps_pubchem_cid_out_of_chembl_molecule_cluster() -> None:
    registry_path = Path(
        "reports/semantic_pipeline_audit/semantic_cluster_registry_2026-07-01.json"
    )
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    cluster_lookup = {cluster["cluster_id"]: cluster for cluster in payload["clusters"]}

    chembl_cluster = cluster_lookup["chembl_molecule_identifier"]
    chembl_members = {member["pipeline"] for member in chembl_cluster["members"]}
    assert chembl_members == {
        "chembl_activity",
        "chembl_compound_record",
        "chembl_molecule",
        "composite_activity",
        "composite_molecule",
    }

    pubchem_cluster = cluster_lookup["pubchem_cid_identifier"]
    pubchem_members = {member["pipeline"] for member in pubchem_cluster["members"]}
    assert pubchem_members == {"pubchem_compound"}


def test_semantic_pair_matrix_budget_rejects_newer_generated_snapshot(
    tmp_path: Path,
) -> None:
    reports_dir = tmp_path / "reports" / "semantic_pipeline_audit"
    reports_dir.mkdir(parents=True)
    old_matrix = reports_dir / "semantic_pair_matrix_2026-05-19.csv"
    new_matrix = reports_dir / "semantic_pair_matrix_2026-05-21.csv"
    old_matrix.write_text(PAIR_MATRIX_HEADERS + "\n", encoding="utf-8")
    new_matrix.write_text(PAIR_MATRIX_HEADERS + "\n", encoding="utf-8")

    review_registry = (
        tmp_path / "configs" / "field_registry" / "semantic_audit_review_registry.yaml"
    )
    review_registry.parent.mkdir(parents=True)
    review_registry.write_text("{}", encoding="utf-8")

    budget_path = (
        tmp_path / "configs" / "field_registry" / "semantic_pair_matrix_budget.yaml"
    )
    budget_path.write_text(
        yaml.safe_dump(
            {
                "matrix_path": "reports/semantic_pipeline_audit/semantic_pair_matrix_2026-05-19.csv",
                "review_registry_path": "configs/field_registry/semantic_audit_review_registry.yaml",
                "reviewed_on": "2026-05-19",
                "budgets": {},
                "status_budgets": [],
                "reviewed_critical_rows": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = validate_semantic_pair_matrix_budget(
        repo_root=tmp_path,
        budget_path=budget_path,
        today=date(2026, 5, 22),
    )

    assert any(
        finding.kind == "stale_reviewed_snapshot" for finding in result.findings
    ), [finding.message for finding in result.findings]
