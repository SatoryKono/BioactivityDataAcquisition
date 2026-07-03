"""Closeout guards for root-hygiene technical-debt issues #5581 through #5584."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.ops.support.repo import cleanup_repository


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5581-5584-closeout.json"
ROOT_REGISTRY = ROOT / "configs" / "quality" / "root_hygiene_review_registry.yaml"
REPLAY_INVENTORY = ROOT / "configs" / "quality" / "replay_safe_cleanup_inventory.yaml"
FIXTURE_LEDGER = ROOT / "configs" / "quality" / "fixture_governance_ledger.yaml"
VCR_CATALOG = ROOT / "reports" / "quality" / "vcr-metadata-catalog.json"
FIXTURE_DUPLICATION = (
    ROOT / "reports" / "quality" / "test-fixture-asset-duplication.json"
)
BRONZE_FIXTURE_GAPS = ROOT / "configs" / "base" / "bronze_fixture_gaps.yaml"

EXPECTED_ISSUES = {5581, 5582, 5583, 5584}
TOOLING_ROOTS_WITH_OWNER_DECISIONS = {
    ".agents",
    ".ai",
    ".cache",
    ".gemini",
    ".junie",
    ".npm-cache",
    ".sonarlint",
    ".vibe",
    ".windsurf",
    "caddy",
}
ENV_SURFACES = {".env", ".env.local", "new.env"}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _registry_candidates() -> dict[str, dict[str, Any]]:
    registry = _load_yaml(ROOT_REGISTRY)
    lanes = registry["review_lanes"]
    assert isinstance(lanes, list)
    candidates: dict[str, dict[str, Any]] = {}
    for lane in lanes:
        assert isinstance(lane, dict)
        for candidate in lane["candidates"]:
            assert isinstance(candidate, dict)
            row = dict(candidate)
            for field in (
                "owner",
                "retention_class",
                "retention_action",
                "cleanup_policy",
            ):
                row.setdefault(field, lane.get(field))
            row["lane_id"] = lane["lane_id"]
            row["lane_classification"] = lane["classification"]
            candidates[str(row["path"])] = row
    return candidates


def _root_review_report() -> dict[str, Any]:
    review_evidence = cleanup_repository.collect_root_review_evidence(ROOT)
    mismatches = cleanup_repository.collect_root_policy_mismatches(ROOT)
    return cleanup_repository.build_root_review_evidence_report(
        ROOT,
        mismatches=mismatches,
        review_evidence=review_evidence,
    )


def _cleanup_report() -> dict[str, Any]:
    candidates = cleanup_repository.collect_cleanup_candidates(
        ROOT,
        root_only_local_scan=True,
    )
    review_evidence = cleanup_repository.collect_root_review_evidence(ROOT)
    return cleanup_repository.build_cleanup_classification_report(
        ROOT,
        candidates=candidates,
        review_evidence=review_evidence,
    )


def _root_evidence_rows() -> dict[str, dict[str, Any]]:
    payload = _root_review_report()
    return {
        str(row["path"]): row
        for row in payload["root_review_evidence"]
        if isinstance(row, dict)
    }


def test_closeout_artifact_covers_requested_issues__5581_5584() -> None:
    payload = _load_json(CLOSEOUT)
    issues = payload["issues"]

    assert payload["schema_version"] == "tech-debt-issues-5581-5584-closeout-v1"
    assert payload["debt_budget_outcome"] == "reduced_or_unchanged"
    assert {issue["number"] for issue in issues} == EXPECTED_ISSUES
    assert all(issue["status"] == "closed-ready" for issue in issues)

    for issue in issues:
        for relative_path in issue["evidence"]:
            assert (ROOT / relative_path).exists(), (
                f"Missing closeout evidence for #{issue['number']}: {relative_path}"
            )


def test_issue_5581_tooling_roots_have_owner_decisions_in_registry_and_evidence() -> (
    None
):
    candidates = _registry_candidates()
    evidence = _root_evidence_rows()
    root_evidence = _root_review_report()

    assert root_evidence["summary"]["ROOT_POLICY_MISMATCH"] == 0
    assert TOOLING_ROOTS_WITH_OWNER_DECISIONS <= set(candidates)

    for path in TOOLING_ROOTS_WITH_OWNER_DECISIONS:
        registry_row = candidates[path]
        evidence_row = evidence[path]
        assert registry_row["owner"], path
        assert registry_row["retention_class"], path
        assert registry_row["retention_action"], path
        assert registry_row["cleanup_policy"], path
        assert evidence_row["owner"] == registry_row["owner"]
        assert evidence_row["retention_class"] == registry_row["retention_class"]
        assert evidence_row["retention_action"] == registry_row["retention_action"]
        assert evidence_row["cleanup_policy"] == registry_row["cleanup_policy"]

    assert candidates[".gemini"]["current_live_state"] == "present_curated_root_surface"
    assert candidates[".vibe"]["current_live_state"] == "present_curated_root_surface"


def test_issue_5584_env_surfaces_are_security_review_only_and_not_cleanup_safe() -> (
    None
):
    candidates = _registry_candidates()
    evidence = _root_evidence_rows()
    cleanup_report = _cleanup_report()

    assert (ROOT / ".env.example").exists()
    assert ".env.example" in (ROOT / ".github" / "root-allowlist.txt").read_text(
        encoding="utf-8"
    )

    cleanup_candidate_paths = {
        row["path"] for row in cleanup_report["cleanup_candidates"]
    }
    assert ENV_SURFACES.isdisjoint(cleanup_candidate_paths)

    for path in ENV_SURFACES:
        registry_row = candidates[path]
        evidence_row = evidence[path]
        assert registry_row["lane_classification"] == "security_review_required"
        assert registry_row["canonical_path"] == ".env.example"
        assert (
            registry_row["cleanup_policy"] == "explicit_per_task_user_approval_required"
        )
        assert "security_review" in registry_row["action_if_reintroduced"]
        assert evidence_row["classification"] == "SECURITY_REVIEW_REQUIRED"
        assert evidence_row["registry_classification"] == "security_review_required"


def test_issue_5582_data_retention_families_are_inventory_classified() -> None:
    inventory = _load_yaml(REPLAY_INVENTORY)
    entries = {
        str(entry["id"]): entry
        for entry in inventory["entries"]
        if isinstance(entry, dict)
    }
    runbook = (
        ROOT / "docs" / "05-operations" / "runbooks" / "retention-sensitive-cleanup.md"
    ).read_text(encoding="utf-8")

    expected = {
        "tracked_input_datasets": ("data/input/**", "reproducibility_fixture"),
        "debug_exports": ("data/debug_exports/**", "tracked_debug_evidence"),
        "control_plane_run_manifest": (
            "data/output/control/run_manifest/**",
            "checkpoint_control_plane_state",
        ),
        "checkpoints": ("data/output/checkpoints/**", "checkpoint_control_plane_state"),
        "cached_bronze_snapshots": ("data/output/bronze/**", "local_runtime_output"),
        "silver_gold_outputs": ("data/output/{silver,gold}/**", "local_runtime_output"),
        "quarantine_records": ("data/output/quarantine/**", "local_runtime_output"),
    }

    for entry_id, (path, retention_class) in expected.items():
        entry = entries[entry_id]
        assert entry["path"] == path
        assert entry["retention_class"] == retention_class
        assert entry["dry_run_required"] is True
        assert entry["protection"]
        assert entry["runbook"]

    for fragment in (
        "`data/input/**`",
        "`data/debug_exports/**`",
        "`data/output/control/**`",
        "`data/output/checkpoints/**`",
        "`data/output/silver/**`, `data/output/gold/**`",
        "`data/output/quarantine/**`",
    ):
        assert fragment in runbook


def test_issue_5583_fixture_vcr_and_golden_pruning_remain_inventory_driven() -> None:
    fixture_duplication = _load_json(FIXTURE_DUPLICATION)
    vcr_catalog = _load_json(VCR_CATALOG)
    fixture_ledger = _load_yaml(FIXTURE_LEDGER)
    bronze_gaps = _load_yaml(BRONZE_FIXTURE_GAPS)

    assert fixture_duplication["duplicate_groups"] == 0
    assert fixture_duplication["duplicate_files"] == 0

    totals = vcr_catalog["totals"]
    pruning = vcr_catalog["pruning"]
    assert totals["cassette_count"] == totals["metadata_sidecar_count"]
    assert totals["unowned_cassette_count"] == 0
    assert totals["duplicate_scenario_stem_count"] == 0
    assert pruning["unowned_cassettes"] == []
    assert pruning["metadata_review_required_cassettes"] == []
    assert all(
        provider["metadata_coverage_percent"] == 100.0
        for provider in vcr_catalog["providers"].values()
    )

    assert bronze_gaps["gaps"] == {}
    policy = fixture_ledger["pruning_policy"]
    assert policy["linked_issue"] == "#5583"
    assert policy["default_action"] == "retain"
    assert "filename_age_only" in policy["forbidden_basis"]
    assert "reachability_owner_paths" in policy["required_evidence"]
