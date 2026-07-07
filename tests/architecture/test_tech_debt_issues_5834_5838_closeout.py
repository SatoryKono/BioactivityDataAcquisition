"""Closeout guards for root-hygiene technical-debt issues #5834 through #5838."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5834-5838-closeout.json"
ROOT_REGISTRY = ROOT / "configs" / "quality" / "root_hygiene_review_registry.yaml"
ROOT_ALLOWLIST = ROOT / ".github" / "root-allowlist.txt"
ROOT_REVIEW_REPORT = ROOT / "reports" / "quality" / "root-hygiene-review-evidence.json"
CLEANUP_REPORT = (
    ROOT / "reports" / "quality" / "root-hygiene-cleanup-classification.json"
)
REPORTS_WORKSPACE_REVIEW = (
    ROOT / "reports" / "quality" / "reports-workspace-review.json"
)
DOCKER_RELOCATION_AUDIT = (
    ROOT
    / "docs"
    / "05-operations"
    / "verification"
    / "docker-helper-root-relocation-audit.md"
)

EXPECTED_ISSUES = {5834, 5835, 5836, 5837, 5838}
ENV_SURFACES = {".env", ".env.local", "new.env"}
LOCAL_ONLY_CLUTTER = {
    ".coverage",
    ".scannerwork",
    ".venv-docs",
    ".venv-win",
    ".venv-win-corrupt",
}
LAUNCHER_SHIMS = {
    ".wsl_proxy_env.sh",
    "codex.bat",
    "codex.ps1",
    "run-codex.ps1",
    "run-codex-wsl.ps1",
    "setup-codex-wsl.bat",
    "setup-codex-wsl.ps1",
    "setup-codex-wsl.sh",
}
DOCKER_ROOT_SURFACES = {
    "docker-compose.monitoring.yml",
    "docker-compose.alertmanager.yml",
    "docker-compose.codex.yml",
    "docker-compose.minio.yml",
    "docker-compose.neo4j-audit.yml",
    "docker-compose.neo4j.yml",
    "docker-compose.redis.yml",
    "docker-compose.sonarqube.yml",
    "docker-compose.yml",
    "docker-setup.ps1",
    "docker-setup.sh",
    "Dockerfile.bioetl",
    "Dockerfile.mcp-fetch",
    "Dockerfile.mcp-filesystem",
    "Dockerfile.mcp-github",
    "Dockerfile.mcp-memory",
    "Dockerfile.warp",
    "grafana-datasource.yml",
}
REHOMED_DOCKER_SURFACES = {
    "docker-compose.alertmanager.yml",
    "docker-compose.minio.yml",
    "docker-compose.redis.yml",
    "docker-compose.sonarqube.yml",
    "Dockerfile.mcp-fetch",
    "Dockerfile.mcp-filesystem",
    "Dockerfile.mcp-github",
    "Dockerfile.mcp-memory",
    "Dockerfile.warp",
    "grafana-datasource.yml",
}
OWNER_DECISION_CLASSIFICATIONS = {
    "owner_decision_required",
    "owner_decision_resolved",
}


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
            row["lane_id"] = lane["lane_id"]
            row["lane_classification"] = lane["classification"]
            for field in (
                "owner",
                "retention_class",
                "retention_action",
                "cleanup_policy",
            ):
                row.setdefault(field, lane.get(field))
            candidates[str(row["path"])] = row
    return candidates


def _root_review_rows() -> dict[str, dict[str, Any]]:
    payload = _load_json(ROOT_REVIEW_REPORT)
    return {
        str(row["path"]): row
        for row in payload["root_review_evidence"]
        if isinstance(row, dict)
    }


def test_closeout_artifact_covers_requested_issues_5834_5838() -> None:
    payload = _load_json(CLOSEOUT)
    issues = payload["issues"]

    assert payload["schema_version"] == "tech-debt-issues-5834-5838-closeout-v1"
    assert payload["debt_budget_outcome"] == "reduced_or_unchanged"
    assert {issue["number"] for issue in issues} == EXPECTED_ISSUES
    assert all(issue["status"] == "closed-ready" for issue in issues)

    for issue in issues:
        for relative_path in issue["evidence"]:
            assert (ROOT / relative_path).exists(), (
                f"Missing closeout evidence for #{issue['number']}: {relative_path}"
            )


def test_issue_5834_live_baseline_cleanup_and_owner_review_artifacts_are_current() -> (
    None
):
    payload = _load_json(CLOSEOUT)
    outcome = payload["outcomes"]["5834"]
    committed_review = _load_json(ROOT_REVIEW_REPORT)
    committed_cleanup = _load_json(CLEANUP_REPORT)

    assert committed_review["summary"]["ROOT_POLICY_MISMATCH"] == 0
    assert committed_review["summary"] == outcome["committed_root_review_summary"]
    assert committed_cleanup["summary"] == outcome["committed_cleanup_summary"]
    assert len(committed_review["root_review_evidence"]) == outcome["root_review_rows"]
    assert len(committed_cleanup["cleanup_candidates"]) == outcome["cleanup_candidates"]
    assert REPORTS_WORKSPACE_REVIEW.exists()
    assert (
        outcome["reports_workspace_review"]
        == "reports/quality/reports-workspace-review.json"
    )


def test_issue_5835_tolerated_local_only_root_clutter_is_reviewed_without_promoting_it() -> (
    None
):
    payload = _load_json(CLOSEOUT)
    outcome = payload["outcomes"]["5835"]
    candidates = _registry_candidates()
    evidence = _root_review_rows()

    assert set(outcome["reviewed_local_only_root_clutter"]) == LOCAL_ONLY_CLUTTER
    for path in LOCAL_ONLY_CLUTTER:
        registry_row = candidates[path]
        assert registry_row["lane_id"] in {
            "local_runtime_root_dirs",
            "root_transient_helpers_and_outputs",
        }
        assert registry_row["lane_classification"] == "review_required"
        assert path in evidence
        assert evidence[path]["classification"] == "REVIEW_REQUIRED"

    assert (
        candidates[".coverage"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert (
        candidates[".scannerwork"]["current_live_state"] == "absent_from_root_baseline"
    )
    assert (
        candidates[".venv-docs"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert (
        candidates[".venv-win"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert (
        candidates[".venv-win-corrupt"]["current_live_state"]
        == "absent_from_root_baseline"
    )


def test_issue_5836_root_env_surfaces_remain_security_review_only() -> None:
    payload = _load_json(CLOSEOUT)
    outcome = payload["outcomes"]["5836"]
    candidates = _registry_candidates()
    evidence = _root_review_rows()
    cleanup_report = _load_json(CLEANUP_REPORT)

    assert outcome["canonical_root_env_template"] == ".env.example"
    assert ".env.example" in ROOT_ALLOWLIST.read_text(encoding="utf-8")

    cleanup_candidate_paths = {
        row["path"] for row in cleanup_report["cleanup_candidates"]
    }
    assert ENV_SURFACES.isdisjoint(cleanup_candidate_paths)

    for path in ENV_SURFACES:
        registry_row = candidates[path]
        evidence_row = evidence[path]
        assert registry_row["lane_id"] == "root_env_security"
        assert registry_row["lane_classification"] == "security_review_required"
        assert registry_row["canonical_path"] == ".env.example"
        assert evidence_row["classification"] == "SECURITY_REVIEW_REQUIRED"
        assert evidence_row["registry_classification"] == "security_review_required"


def test_issue_5837_root_codex_wsl_shims_stay_thin_and_owner_anchored() -> None:
    payload = _load_json(CLOSEOUT)
    outcome = payload["outcomes"]["5837"]
    candidates = _registry_candidates()
    evidence = _root_review_rows()

    assert set(outcome["reviewed_root_shims"]) == LAUNCHER_SHIMS
    for path in LAUNCHER_SHIMS:
        registry_row = candidates[path]
        evidence_row = evidence[path]
        assert registry_row["lane_id"] == "root_launcher_shims"
        assert registry_row["lane_classification"] in OWNER_DECISION_CLASSIFICATIONS
        assert evidence_row["classification"] == "REVIEW_REQUIRED"

    assert candidates["codex.ps1"]["canonical_path"] == "scripts/ai/codex/run-codex.ps1"
    assert (
        candidates["setup-codex-wsl.bat"]["canonical_path"]
        == "scripts/ai/codex/setup-codex-wsl.bat"
    )
    assert (
        candidates[".wsl_proxy_env.sh"]["canonical_path"]
        == "scripts/ai/codex/helper/wsl_proxy_env.sh"
    )


def test_issue_5838_root_docker_adjuncts_are_reviewed_and_evidence_backed() -> None:
    payload = _load_json(CLOSEOUT)
    outcome = payload["outcomes"]["5838"]
    candidates = _registry_candidates()
    evidence = _root_review_rows()

    assert DOCKER_RELOCATION_AUDIT.exists()
    assert set(outcome["reviewed_root_docker_surfaces"]) == DOCKER_ROOT_SURFACES

    allowlist_text = ROOT_ALLOWLIST.read_text(encoding="utf-8")
    for path in DOCKER_ROOT_SURFACES:
        registry_row = candidates[path]
        evidence_row = evidence[path]
        if path in REHOMED_DOCKER_SURFACES:
            assert path not in allowlist_text
            assert registry_row["current_live_state"] == "absent_from_root_baseline"
        else:
            assert path in allowlist_text
            assert registry_row["current_live_state"] == "present_approved_root_surface"
        assert registry_row["lane_id"] == "root_docker_adjuncts"
        # Lane classification changed from owner_decision_required to owner_decision_resolved
        assert registry_row["lane_classification"] in {
            "owner_decision_required",
            "owner_decision_resolved",
        }
        assert registry_row["owner"] == "Engineering / Runtime Platform"
        assert registry_row["disposition"] in {
            "moved_to_owned_path",
            "must_stay_root",
            "temporary_shim",
        }
        assert evidence_row["classification"] == "REVIEW_REQUIRED"

    assert (
        candidates["docker-setup.ps1"]["canonical_path"]
        == "scripts/ops/docker-setup.ps1"
    )
    assert (
        candidates["docker-setup.sh"]["canonical_path"] == "scripts/ops/docker-setup.sh"
    )
    assert candidates["Dockerfile.bioetl"]["canonical_path"] == "Dockerfile.bioetl"
    assert (
        candidates["Dockerfile.warp"]["canonical_path"]
        == "scripts/ops/runtime/docker/images/warp/Dockerfile"
    )
    assert (
        candidates["grafana-datasource.yml"]["canonical_path"]
        == "grafana/provisioning/datasources-local/grafana-datasource.yml"
    )
