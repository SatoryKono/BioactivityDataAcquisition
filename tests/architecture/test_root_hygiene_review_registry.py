"""Architecture tests for root-hygiene remediation review registry."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "configs" / "quality" / "root_hygiene_review_registry.yaml"
STRUCTURE_CATALOG_PATH = ROOT / "configs" / "quality" / "repo_structure_catalog.yaml"
ROOT_POLICY_DOC_PATH = ROOT / "docs" / "00-project" / "governance" / "03-file-policy.md"
REMEDIATION_PLAN_PATH = (
    ROOT / "docs" / "plans" / "repository-file-structure-remediation-plan-2026-04-28.md"
)

ALLOWED_CLASSIFICATIONS = {
    "blocked_cleanup_zone",
    "cleanup_completed",
    "owner_decision_required",
    "owner_decision_resolved",
    "review_required",
    "security_review_required",
}
ALLOWED_LIVE_STATES = {
    "absent_from_root_baseline",
    "present_approved_root_surface",
    "present_blocked_cleanup_zone",
    "present_curated_root_surface",
    "present_local_only_root_surface",
}


def _load_yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{path} must contain a YAML object"
    return payload


def test_root_hygiene_review_registry_declares_live_green_baseline() -> None:
    payload = _load_yaml(REGISTRY_PATH)

    assert payload.get("status") == "active"
    baseline = payload.get("current_live_root_baseline")
    assert isinstance(baseline, dict), "Expected current_live_root_baseline object"
    assert baseline.get("tracked_root_audit_status") == "pass"
    assert baseline.get("strict_untracked_root_audit_status") == "pass"
    command = str(baseline.get("verification_command", ""))
    assert "audit_root_cleanliness.py --strict-untracked" in command


def test_root_hygiene_review_registry_candidates_are_unique_and_grounded() -> None:
    payload = _load_yaml(REGISTRY_PATH)
    lanes = payload.get("review_lanes")
    assert isinstance(lanes, list), "Expected review_lanes list"

    seen_paths: set[str] = set()
    lane_ids: set[str] = set()
    for lane in lanes:
        assert isinstance(lane, dict), "Each lane must be an object"
        lane_id = lane.get("lane_id")
        assert isinstance(lane_id, str) and lane_id, "Each lane needs lane_id"
        assert lane_id not in lane_ids, f"Duplicate lane_id: {lane_id}"
        lane_ids.add(lane_id)

        classification = lane.get("classification")
        assert classification in ALLOWED_CLASSIFICATIONS, (
            f"Unexpected lane classification for {lane_id}: {classification}"
        )

        verification = lane.get("verification")
        assert isinstance(verification, list) and verification, (
            f"Lane {lane_id} must declare verification commands"
        )

        candidates = lane.get("candidates")
        assert isinstance(candidates, list) and candidates, (
            f"Lane {lane_id} must contain at least one candidate"
        )
        for candidate in candidates:
            assert isinstance(candidate, dict), "Candidate entries must be objects"
            path = candidate.get("path")
            assert isinstance(path, str) and path, "Candidate path must be a string"
            assert path not in seen_paths, f"Duplicate candidate path: {path}"
            seen_paths.add(path)

            live_state = candidate.get("current_live_state")
            assert live_state in ALLOWED_LIVE_STATES, (
                f"Unexpected current_live_state for {path}: {live_state}"
            )

            canonical_path = candidate.get("canonical_path")
            if isinstance(canonical_path, str) and canonical_path:
                assert (ROOT / canonical_path).exists(), (
                    f"Canonical path for {path} does not exist: {canonical_path}"
                )


def test_root_hygiene_review_registry_tracks_absent_root_conftest_surface() -> None:
    payload = _load_yaml(REGISTRY_PATH)
    lanes = payload.get("review_lanes")
    assert isinstance(lanes, list), "Expected review_lanes list"

    conftest_candidate = next(
        candidate
        for lane in lanes
        if isinstance(lane, dict)
        for candidate in lane.get("candidates", [])
        if isinstance(candidate, dict) and candidate.get("path") == "conftest.py"
    )

    assert conftest_candidate["current_live_state"] == "absent_from_root_baseline"
    assert conftest_candidate["canonical_path"] == "tests/conftest.py"


def test_root_hygiene_review_registry_tracks_observed_transient_root_families() -> None:
    payload = _load_yaml(REGISTRY_PATH)
    lanes = payload.get("review_lanes")
    assert isinstance(lanes, list), "Expected review_lanes list"

    transient_lane = next(
        lane
        for lane in lanes
        if isinstance(lane, dict)
        and lane.get("lane_id") == "root_transient_helpers_and_outputs"
    )
    candidates = transient_lane["candidates"]
    assert isinstance(candidates, list)
    by_path = {
        candidate["path"]: candidate
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("path"), str)
    }

    assert (
        by_path["artifacts"]["current_live_state"] == "present_local_only_root_surface"
    )
    assert by_path["artifacts"]["canonical_path"] is None
    assert (
        by_path[".coverage"]["current_live_state"] == "present_local_only_root_surface"
    )
    assert (
        by_path["coverage.xml"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert (
        by_path["Test Results - Pytest_All.html"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert (
        by_path["Test Results - Pytest_All.xml"]["current_live_state"]
        == "absent_from_root_baseline"
    )
    assert by_path[".xml"]["current_live_state"] == "present_local_only_root_surface"
    assert (
        by_path["mcp-shell.log"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert (
        by_path["_tmp_panel_inventory.mjs"]["current_live_state"]
        == "absent_from_root_baseline"
    )
    assert (
        by_path["_tmp_panel_inventory.ps1"]["current_live_state"]
        == "absent_from_root_baseline"
    )
    assert (
        by_path["temp_analyze_conflicting.py"]["current_live_state"]
        == "absent_from_root_baseline"
    )
    assert (
        by_path["temp_get_hash.py"]["current_live_state"] == "absent_from_root_baseline"
    )
    assert (
        by_path["test_output.txt"]["current_live_state"] == "absent_from_root_baseline"
    )
    assert by_path["tests.txt"]["current_live_state"] == "absent_from_root_baseline"


def test_root_hygiene_review_registry_classifies_live_local_runtime_root_surfaces() -> (
    None
):
    payload = _load_yaml(REGISTRY_PATH)
    lanes = payload.get("review_lanes")
    assert isinstance(lanes, list), "Expected review_lanes list"

    local_runtime_lane = next(
        lane
        for lane in lanes
        if isinstance(lane, dict) and lane.get("lane_id") == "local_runtime_root_dirs"
    )
    candidates = local_runtime_lane["candidates"]
    assert isinstance(candidates, list)
    by_path = {
        candidate["path"]: candidate
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("path"), str)
    }

    assert by_path[".codex_tmp"]["current_live_state"] == "absent_from_root_baseline"
    assert (
        by_path[".benchmarks"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert (
        by_path[".hypothesis"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert (
        by_path[".import_linter_cache"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert (
        by_path[".mypy_cache"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert (
        by_path[".coverage-sharded-current-main"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert (
        by_path["node_modules"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert (
        by_path[".pytest_cache"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert (
        by_path[".ruff_cache"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert by_path[".scannerwork"]["current_live_state"] == "absent_from_root_baseline"
    assert (
        by_path["test-output"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert by_path["tmp"]["current_live_state"] == "present_local_only_root_surface"
    assert by_path["~"]["current_live_state"] == "present_local_only_root_surface"
    assert by_path[".venv"]["current_live_state"] == "present_local_only_root_surface"
    assert (
        by_path[".venv-docs"]["current_live_state"] == "present_local_only_root_surface"
    )
    assert (
        by_path[".venv-win"]["current_live_state"] == "present_local_only_root_surface"
    )
    assert (
        by_path[".venv-win-corrupt"]["current_live_state"]
        == "absent_from_root_baseline"
    )


def test_root_hygiene_review_registry_classifies_qodo_as_local_vendor_surface() -> None:
    payload = _load_yaml(REGISTRY_PATH)
    lanes = payload.get("review_lanes")
    assert isinstance(lanes, list), "Expected review_lanes list"

    vendor_lane = next(
        lane
        for lane in lanes
        if isinstance(lane, dict)
        and lane.get("lane_id") == "local_vendor_tooling_roots"
    )
    candidates = vendor_lane["candidates"]
    assert isinstance(candidates, list)
    by_path = {
        candidate["path"]: candidate
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("path"), str)
    }

    assert by_path[".qodo"]["current_live_state"] == "present_local_only_root_surface"


def test_root_hygiene_review_registry_tracks_absent_root_logs_and_test_print() -> None:
    payload = _load_yaml(REGISTRY_PATH)
    lanes = payload.get("review_lanes")
    assert isinstance(lanes, list), "Expected review_lanes list"

    transient_lane = next(
        lane
        for lane in lanes
        if isinstance(lane, dict)
        and lane.get("lane_id") == "root_transient_helpers_and_outputs"
    )
    transient_by_path = {
        candidate["path"]: candidate
        for candidate in transient_lane["candidates"]
        if isinstance(candidate, dict) and isinstance(candidate.get("path"), str)
    }
    assert (
        transient_by_path["logs"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert transient_by_path["logs"]["canonical_path"] == "reports/logs"

    ad_hoc_lane = next(
        lane
        for lane in lanes
        if isinstance(lane, dict)
        and lane.get("lane_id") == "root_ad_hoc_docs_and_diagnostics"
    )
    ad_hoc_by_path = {
        candidate["path"]: candidate
        for candidate in ad_hoc_lane["candidates"]
        if isinstance(candidate, dict) and isinstance(candidate.get("path"), str)
    }
    assert (
        ad_hoc_by_path["test_print.py"]["current_live_state"]
        == "absent_from_root_baseline"
    )


def test_blocked_cleanup_lane_matches_structure_catalog() -> None:
    registry = _load_yaml(REGISTRY_PATH)
    structure_catalog = _load_yaml(STRUCTURE_CATALOG_PATH)

    lanes = registry["review_lanes"]
    assert isinstance(lanes, list)
    blocked_lane = next(
        lane
        for lane in lanes
        if isinstance(lane, dict)
        and lane.get("lane_id") == "retention_sensitive_boundaries"
    )
    blocked_candidates = blocked_lane["candidates"]
    assert isinstance(blocked_candidates, list)

    lane_paths = {candidate["path"] for candidate in blocked_candidates}
    catalog_zones = structure_catalog.get("blocked_cleanup_zones")
    assert isinstance(catalog_zones, list), "blocked_cleanup_zones must be a list"
    catalog_paths = {
        zone["path"]
        for zone in catalog_zones
        if isinstance(zone, dict) and "path" in zone
    }

    assert lane_paths == catalog_paths

    catalog_runbooks = {
        zone["path"]: zone.get("cleanup_runbook")
        for zone in catalog_zones
        if isinstance(zone, dict) and "path" in zone
    }
    for candidate in blocked_candidates:
        assert candidate.get("cleanup_runbook") == catalog_runbooks[candidate["path"]]


def test_root_tooling_transition_lane_tracks_script_codex_as_local_only() -> None:
    registry = _load_yaml(REGISTRY_PATH)
    lanes = registry["review_lanes"]
    assert isinstance(lanes, list)

    transition_lane = next(
        lane
        for lane in lanes
        if isinstance(lane, dict) and lane.get("lane_id") == "root_tooling_transitions"
    )
    candidates = transition_lane["candidates"]
    assert isinstance(candidates, list)
    by_path = {
        candidate["path"]: candidate
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("path"), str)
    }

    assert (
        by_path["script-codex"]["current_live_state"]
        == "present_local_only_root_surface"
    )
    assert by_path["script-codex"]["canonical_path"] == "scripts/ai/codex"


def test_root_reviewed_human_facing_docs_lane_tracks_best_practices() -> None:
    registry = _load_yaml(REGISTRY_PATH)
    lanes = registry["review_lanes"]
    assert isinstance(lanes, list)

    docs_lane = next(
        lane
        for lane in lanes
        if isinstance(lane, dict)
        and lane.get("lane_id") == "root_reviewed_human_facing_docs"
    )
    candidates = docs_lane["candidates"]
    assert isinstance(candidates, list)
    by_path = {
        candidate["path"]: candidate
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("path"), str)
    }

    assert (
        by_path["best_practices.md"]["current_live_state"]
        == "present_approved_root_surface"
    )
    assert (
        by_path["best_practices.md"]["canonical_path"]
        == "docs/00-project/governance/qodo/README.md"
    )


def test_root_review_contract_entrypoints_have_exact_filename_owners() -> None:
    registry = _load_yaml(REGISTRY_PATH)
    lanes = registry["review_lanes"]
    assert isinstance(lanes, list)

    contract_lane = next(
        lane
        for lane in lanes
        if isinstance(lane, dict)
        and lane.get("lane_id") == "root_review_contract_entrypoints"
    )
    assert contract_lane["owner"] == "Engineering / Review Tooling"
    assert contract_lane["retention_class"] == "reviewed_exact_filename_tool_contract"

    candidates = contract_lane["candidates"]
    assert isinstance(candidates, list)
    by_path = {
        candidate["path"]: candidate
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("path"), str)
    }

    assert set(by_path) == {
        ".coderabbit.yaml",
        "commitlint.config.mjs",
        "mint.json",
        "pr_compliance_checklist.yaml",
        "sonar-project.properties",
    }
    present_contract_paths = {".coderabbit.yaml", "commitlint.config.mjs"}
    for path in present_contract_paths:
        candidate = by_path[path]
        assert candidate["current_live_state"] == "present_approved_root_surface"
        assert candidate["canonical_path"] == path
    assert by_path["mint.json"]["current_live_state"] == "absent_from_root_baseline"
    assert by_path["mint.json"]["canonical_path"] is None
    assert (
        by_path["pr_compliance_checklist.yaml"]["current_live_state"]
        == "absent_from_root_baseline"
    )
    assert by_path["pr_compliance_checklist.yaml"]["canonical_path"] is None
    assert (
        by_path["sonar-project.properties"]["current_live_state"]
        == "absent_from_root_baseline"
    )
    assert by_path["sonar-project.properties"]["canonical_path"] is None


def test_no_tracked_repository_root_scripts_remain() -> None:
    completed = subprocess.run(
        ["git", "ls-files", "-z", "*.sh", "*.ps1", "*.py", "*.bat"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    root_scripts = sorted(
        path
        for path in completed.stdout.decode("utf-8", errors="replace").split("\0")
        if path and "/" not in path
    )

    assert root_scripts == []


def test_root_launcher_shims_lane_tracks_retired_root_entrypoints() -> None:
    registry = _load_yaml(REGISTRY_PATH)
    lanes = registry["review_lanes"]
    assert isinstance(lanes, list)

    shim_lane = next(
        lane
        for lane in lanes
        if isinstance(lane, dict) and lane.get("lane_id") == "root_launcher_shims"
    )
    candidates = shim_lane["candidates"]
    assert isinstance(candidates, list)
    by_path = {
        candidate["path"]: candidate
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("path"), str)
    }

    assert shim_lane["classification"] == "owner_decision_resolved"
    assert shim_lane["cleanup_policy"] == (
        "do_not_restore_root_shims_without_fresh_owner_review"
    )

    expected_canonical_paths = {
        ".wsl_proxy_env.sh": "scripts/engineering/dev/bash/.wsl_proxy_env.sh",
        "codex.bat": "scripts/ops/codex.bat",
        "codex.ps1": "scripts/ai/codex/run-codex.ps1",
        "run-codex.ps1": "scripts/ai/codex/run-codex.ps1",
        "run-codex-wsl.ps1": "scripts/ai/codex/run-codex.ps1",
        "setup-codex-wsl.bat": "scripts/ai/codex/setup-codex-wsl.bat",
        "setup-codex-wsl.ps1": "scripts/ai/codex/setup.ps1",
        "setup-codex-wsl.sh": "scripts/ai/codex/helper/setup-wsl-complete.sh",
    }
    assert set(by_path) == set(expected_canonical_paths)

    for path, canonical_path in expected_canonical_paths.items():
        assert by_path[path]["current_live_state"] == "absent_from_root_baseline"
        assert by_path[path]["canonical_path"] == canonical_path
        assert (ROOT / path).exists() is False
        assert (ROOT / canonical_path).exists()

    assert by_path["codex.ps1"]["canonical_path"] == "scripts/ai/codex/run-codex.ps1"
    assert by_path["codex.bat"]["canonical_path"] == "scripts/ops/codex.bat"
    assert by_path[".wsl_proxy_env.sh"]["canonical_path"] == (
        "scripts/engineering/dev/bash/.wsl_proxy_env.sh"
    )


def test_root_docker_adjunct_lane_tracks_reviewed_root_docker_surfaces() -> None:
    registry = _load_yaml(REGISTRY_PATH)
    lanes = registry["review_lanes"]
    assert isinstance(lanes, list)

    docker_lane = next(
        lane
        for lane in lanes
        if isinstance(lane, dict) and lane.get("lane_id") == "root_docker_adjuncts"
    )
    assert docker_lane["classification"] == "owner_decision_resolved"
    assert docker_lane["cleanup_policy"].startswith(
        "resolved_docker_helper_disposition"
    )
    candidates = docker_lane["candidates"]
    assert isinstance(candidates, list)
    by_path = {
        candidate["path"]: candidate
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("path"), str)
    }

    expected_root_surfaces = {
        "docker-compose.monitoring.yml",
        "docker-compose.alertmanager.yml",
        "docker-compose.minio.yml",
        "docker-compose.neo4j-audit.yml",
        "docker-compose.neo4j.yml",
        "docker-compose.redis.yml",
        "docker-compose.sonarqube.yml",
        "docker-compose.yml",
        "docker-setup.ps1",
        "docker-setup.sh",
        "Dockerfile.bioetl",
        "grafana-datasource.yml",
    }
    assert expected_root_surfaces == set(by_path)

    rehomed_surfaces = {
        "docker-compose.alertmanager.yml",
        "docker-compose.minio.yml",
        "docker-compose.redis.yml",
        "docker-compose.sonarqube.yml",
        "docker-setup.ps1",
        "docker-setup.sh",
        "grafana-datasource.yml",
    }
    for path in expected_root_surfaces - rehomed_surfaces:
        assert by_path[path]["current_live_state"] == "present_approved_root_surface"
    for path in rehomed_surfaces:
        assert by_path[path]["current_live_state"] == "absent_from_root_baseline"

    expected_dispositions = {
        "docker-compose.monitoring.yml": "must_stay_root",
        "docker-compose.neo4j-audit.yml": "must_stay_root",
        "docker-compose.neo4j.yml": "must_stay_root",
        "docker-compose.yml": "must_stay_root",
        "Dockerfile.bioetl": "must_stay_root",
    }
    for path, disposition in expected_dispositions.items():
        assert by_path[path]["disposition"] == disposition
    for path in rehomed_surfaces:
        assert by_path[path]["disposition"] == "moved_to_owned_path"

    assert (
        by_path["docker-setup.ps1"]["canonical_path"] == "scripts/ops/docker-setup.ps1"
    )
    assert by_path["docker-setup.sh"]["canonical_path"] == "scripts/ops/docker-setup.sh"
    assert by_path["Dockerfile.bioetl"]["canonical_path"] == "Dockerfile.bioetl"
    assert (
        by_path["grafana-datasource.yml"]["canonical_path"]
        == "grafana/provisioning/datasources-local/grafana-datasource.yml"
    )


def test_root_policy_declares_target_root_model_and_docker_dispositions() -> None:
    text = ROOT_POLICY_DOC_PATH.read_text(encoding="utf-8")

    for required_phrase in (
        "Target root model",
        "Mandatory root minimum",
        "Tool-required root files",
        "Human-facing root docs",
        "Allowed root directories",
        "Forbidden root files/directories",
        "Temporary compatibility surfaces",
        "MUST stay root",
        "retired root script",
        "MUST NOT be restored",
        "moved to owned path",
        "docs/05-operations/verification/docker-helper-root-relocation-audit.md",
        "configs/quality/generated_artifact_routing.yaml",
    ):
        assert required_phrase in text


def test_remediation_plan_links_github_issue_set_and_required_sources() -> None:
    text = REMEDIATION_PLAN_PATH.read_text(encoding="utf-8")

    for issue_ref in ("#3219", "#3223", "#3226", "#3227"):
        assert issue_ref in text

    for required_reference in (
        ".github/root-allowlist.txt",
        "configs/quality/repo_structure_catalog.yaml",
        "docs/05-operations/runbooks/retention-sensitive-cleanup.md",
        "configs/quality/scripts_lifecycle_registry.json",
        "configs/quality/root_hygiene_review_registry.yaml",
    ):
        assert required_reference in text

    assert "root-hygiene" in text
    assert "401" in text
    assert "owner/admin verification" in text
