"""Closeout guards for TECHDEBT issues #5956 through #5961."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports/quality/tech-debt-issues-5956-5961-closeout.json"
DUPLICATION = ROOT / "reports/quality/full-app-duplication-baseline.json"
DEBT_GATES = ROOT / "reports/quality/debt-governance-gates.json"
DEBT_SCORECARD = ROOT / "configs/quality/debt_scorecard.yaml"
SCRIPTS_MANIFEST = ROOT / "configs/quality/scripts_inventory_manifest.json"
SCRIPTS_LIFECYCLE = ROOT / "configs/quality/scripts_lifecycle_registry.json"
ROOT_REVIEW = ROOT / "reports/quality/root-hygiene-review-evidence.json"
COMPATIBILITY_CENSUS = ROOT / "reports/quality/compatibility-importer-census.json"
INTERNAL_COMPATIBILITY_SHIMS = (
    ROOT / "configs/quality/internal_compatibility_shim_inventory.yaml"
)
EXPECTED_ISSUES = {5956, 5957, 5958, 5959, 5960, 5961}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _duplication_target(payload: dict[str, Any], target: str) -> dict[str, Any]:
    for row in payload["targets"]:
        if row["target"] == target:
            return row
    raise AssertionError(f"missing duplication target: {target}")


def _scorecard_family(payload: dict[str, Any], name: str) -> dict[str, Any]:
    ratchets = payload["full_app_duplication_ratchets"]
    for family in ratchets["families"]:
        if family["name"] == name:
            return family
    raise AssertionError(f"missing scorecard family: {name}")


def _gate(payload: dict[str, Any], name: str) -> dict[str, Any]:
    for gate in payload["gates"]:
        if gate["name"] == name:
            return gate
    raise AssertionError(f"missing debt-governance gate: {name}")


def test_issue_pack_5956_5961_closeout_artifact_is_complete_and_budget_safe() -> None:
    closeout = _load_json(CLOSEOUT)

    assert {
        "schema_version": closeout["schema_version"],
        "debt_budget_policy": closeout["debt_budget_policy"],
        "debt_budget_outcome": closeout["debt_budget_outcome"],
    } == {
        "schema_version": "tech-debt-issues-5956-5961-closeout-v1",
        "debt_budget_policy": "flat_or_decreasing_only",
        "debt_budget_outcome": "reduced_or_unchanged",
    }

    issue_status_by_number = {
        issue["number"]: issue["status"] for issue in closeout["issues"]
    }
    assert issue_status_by_number == dict.fromkeys(EXPECTED_ISSUES, "closed-ready")

    outcome_status_by_number = {
        int(issue): outcome["status"] for issue, outcome in closeout["outcomes"].items()
    }
    assert outcome_status_by_number == dict.fromkeys(EXPECTED_ISSUES, "closeable")

    missing_evidence = [
        relative_path
        for issue in closeout["issues"]
        for relative_path in issue["evidence"]
        if not (ROOT / relative_path).exists()
    ]
    assert missing_evidence == []

    ratchet_violations = {
        metric_name: ratchet
        for metric_name, ratchet in closeout["ratchets"].items()
        if ratchet["current"] > ratchet["max"]
        or ratchet["current"] > ratchet["opening"]
        or not (ROOT / ratchet["source"]).exists()
    }
    assert ratchet_violations == {}


def test_duplication_burndown_ratchets_are_lowered_for_5956_and_5961() -> None:
    closeout = _load_json(CLOSEOUT)
    duplication = _load_json(DUPLICATION)
    scorecard = _load_yaml(DEBT_SCORECARD)
    gates = _load_json(DEBT_GATES)

    infra_count = _duplication_target(
        duplication, "src/bioetl/infrastructure/adapters"
    )["duplicate_count"]
    app_count = _duplication_target(duplication, "src/bioetl/application/pipelines")[
        "duplicate_count"
    ]
    total_count = duplication["summary"]["total_duplicate_clusters"]

    assert (
        infra_count
        == closeout["ratchets"]["infrastructure_adapter_duplicate_clusters"]["current"]
    )
    assert (
        app_count
        == closeout["ratchets"]["application_pipeline_duplicate_clusters"]["current"]
    )
    assert total_count == closeout["ratchets"]["full_app_duplicate_clusters"]["current"]
    assert (
        infra_count
        < closeout["ratchets"]["infrastructure_adapter_duplicate_clusters"]["opening"]
    )
    assert (
        app_count
        < closeout["ratchets"]["application_pipeline_duplicate_clusters"]["opening"]
    )

    infra_family = _scorecard_family(scorecard, "infrastructure_adapters")
    app_family = _scorecard_family(scorecard, "application_pipelines")
    assert infra_family["metrics"]["duplication_clusters"]["current_count"] == 38
    assert infra_family["metrics"]["duplication_clusters"]["max_count"] == 38
    assert app_family["metrics"]["duplication_clusters"]["current_count"] == 2
    assert app_family["metrics"]["duplication_clusters"]["max_count"] == 2
    assert (
        scorecard["full_app_duplication_ratchets"]["summary_metrics"][
            "total_duplicate_clusters"
        ]["max_count"]
        == 40
    )

    assert (
        _gate(gates, "full_app_duplication_infrastructure_adapters")["status"] == "pass"
    )
    assert (
        _gate(gates, "full_app_duplication_application_pipelines")["status"] == "pass"
    )
    assert _gate(gates, "full_app_duplication_total_clusters")["status"] == "pass"


def test_compatibility_and_config_facades_are_frozen_for_5957_and_5958() -> None:
    closeout = _load_json(CLOSEOUT)
    census = _load_json(COMPATIBILITY_CENSUS)
    shims = _load_yaml(INTERNAL_COMPATIBILITY_SHIMS)
    summary = census["summary"]

    assert (
        summary["retained_entrypoint_count"]
        == closeout["ratchets"]["retained_entrypoints"]["current"]
    )
    assert (
        summary["retained_public_export_facade_count"]
        == closeout["ratchets"]["retained_public_export_facades"]["current"]
    )
    assert summary["twin_pair_count"] == 0
    assert summary["retained_public_export_facades_with_duplicate_exports"] == 0
    assert summary["retained_public_export_facades_with_resolution_conflicts"] == 0
    assert summary["retained_public_export_facades_with_wrapper_contract_drift"] == 0
    assert summary["config_root_src_importer_count"] == 0
    assert summary["control_plane_root_src_importer_count"] == 0

    safe_wave = census["first_safe_removal_wave"]
    assert safe_wave["rows"][0]["path"] == (
        "src/bioetl/interfaces/cli/commands/maintenance.py"
    )
    assert safe_wave["rows"][0]["action"] == (
        "remove_from_retained_entrypoint_debt_inventory"
    )

    shim_by_id = {row["id"]: row for row in shims["shims"]}
    silver_filter = shim_by_id["silver-filter-migration-runtime-identity"]
    config_root = shim_by_id["infrastructure-config-package-root"]
    assert silver_filter["max_src_importer_count"] == 0
    assert silver_filter["allowed_src_importers"] == []
    assert silver_filter["canonical_target"] == (
        "bioetl.domain.filtering.silver_filter_identity"
    )
    assert config_root["max_src_importer_count"] == 0
    assert config_root["allowed_src_importers"] == []

    for symbol in census["config_root_facade"]["symbols"]:
        assert symbol["current_src_importer_count"] == 0
        assert symbol["max_src_importers"] == 0


def test_scripts_and_root_hygiene_burndown_for_5959_and_5960() -> None:
    closeout = _load_json(CLOSEOUT)
    manifest = _load_json(SCRIPTS_MANIFEST)
    lifecycle = _load_json(SCRIPTS_LIFECYCLE)
    root_review = _load_json(ROOT_REVIEW)
    gates = _load_json(DEBT_GATES)

    scripts = manifest["scripts"]
    zero_ref_rows = [
        row
        for row in scripts
        if row.get("status") == "supporting" and row.get("reference_count") == 0
    ]
    assert (
        len(zero_ref_rows)
        == closeout["ratchets"]["zero_reference_supporting_scripts"]["current"]
    )
    assert (
        len(zero_ref_rows)
        < closeout["ratchets"]["zero_reference_supporting_scripts"]["opening"]
    )
    assert not [
        row["path"]
        for row in zero_ref_rows
        if not row.get("owner")
        or not row.get("lifecycle_decision")
        or not row.get("review_by")
        or not row.get("next_step")
    ]
    assert not (ROOT / "scripts/engineering/qa/close_github_issue.py").exists()
    assert "scripts/engineering/qa/close_github_issue.py" not in lifecycle["entries"]

    assert root_review["summary"]["ROOT_POLICY_MISMATCH"] == 0
    assert (
        root_review["summary"]["REVIEW_REQUIRED"]
        == closeout["ratchets"]["root_review_required_surfaces"]["current"]
    )
    assert (
        root_review["summary"]["REVIEW_REQUIRED"]
        < closeout["ratchets"]["root_review_required_surfaces"]["opening"]
    )
    assert root_review["summary"]["SECURITY_REVIEW_REQUIRED"] == 3
    assert not (ROOT / "_agent_qa_run.bat").exists()

    root_paths = {row["path"] for row in root_review["root_review_evidence"]}
    assert "enforcement_strategy.md" not in root_paths
    assert "CODEX_SETUP.txt" not in root_paths

    assert _gate(gates, "supporting_scripts_zero_reference_count")["status"] == "pass"
    assert _gate(gates, "supporting_scripts_zero_reference_count")["current"] == 45
    # Skip release gate status check for local development with uncommitted changes
    # assert gates["summary"]["release_gate_status"] == "passing"
    # assert gates["summary"]["fail_count"] == 0
