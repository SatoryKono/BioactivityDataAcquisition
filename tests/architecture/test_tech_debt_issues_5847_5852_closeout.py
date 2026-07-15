"""Closeout guards for root-hygiene issues #5847 through #5852."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5847-5852-closeout.json"
ROOT_REGISTRY = ROOT / "configs" / "quality" / "root_hygiene_review_registry.yaml"
ROOT_ALLOWLIST = ROOT / ".github" / "root-allowlist.txt"
DOCKER_CONTRACTS = ROOT / "configs" / "quality" / "docker_helper_contracts.yaml"

EXPECTED_ISSUES = {5847, 5848, 5849, 5850, 5851, 5852}
RETIRED_ROOT_ENTRIES = {
    ".wsl_proxy_env.sh",
    "Dockerfile.mcp-fetch",
    "Dockerfile.mcp-filesystem",
    "Dockerfile.mcp-github",
    "Dockerfile.mcp-memory",
    "Dockerfile.warp",
    "codex.bat",
    "codex.ps1",
    "docker-compose.alertmanager.yml",
    "docker-compose.minio.yml",
    "docker-compose.redis.yml",
    "docker-compose.sonarqube.yml",
    "docker-setup.ps1",
    "docker-setup.sh",
    "grafana-datasource.yml",
    "run-codex.ps1",
    "run-codex-wsl.ps1",
    "setup-codex-wsl.bat",
    "setup-codex-wsl.ps1",
    "setup-codex-wsl.sh",
}
COMPOSE_REHOME_MAP = {
    "docker-compose.alertmanager.yml": "scripts/ops/runtime/docker/compose/alertmanager.yml",
    "docker-compose.minio.yml": "scripts/ops/runtime/docker/compose/minio.yml",
    "docker-compose.redis.yml": "scripts/ops/runtime/docker/compose/redis.yml",
    "docker-compose.sonarqube.yml": "scripts/ops/runtime/docker/compose/sonarqube.yml",
}
IMAGE_REHOME_MAP = {
    "Dockerfile.mcp-fetch": "scripts/ops/runtime/docker/images/mcp-fetch/Dockerfile",
    "Dockerfile.mcp-filesystem": "scripts/ops/runtime/docker/images/mcp-filesystem/Dockerfile",
    "Dockerfile.mcp-github": "scripts/ops/runtime/docker/images/mcp-github/Dockerfile",
    "Dockerfile.mcp-memory": "scripts/ops/runtime/docker/images/mcp-memory/Dockerfile",
    "Dockerfile.warp": "scripts/ops/runtime/docker/images/warp/Dockerfile",
    "grafana-datasource.yml": "grafana/provisioning/datasources-local/grafana-datasource.yml",
}
SUPERSEDED_IMAGE_PATHS = frozenset(IMAGE_REHOME_MAP.values()) - {
    "grafana/provisioning/datasources-local/grafana-datasource.yml"
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _git_ls_files() -> set[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return {
        path
        for path in completed.stdout.decode("utf-8", errors="replace").split("\0")
        if path
    }


def _registry_candidates() -> dict[str, dict[str, Any]]:
    registry = _load_yaml(ROOT_REGISTRY)
    result: dict[str, dict[str, Any]] = {}
    for lane in registry["review_lanes"]:
        assert isinstance(lane, dict)
        for candidate in lane["candidates"]:
            assert isinstance(candidate, dict)
            row = dict(candidate)
            row["lane_id"] = lane["lane_id"]
            row["owner"] = lane.get("owner")
            row["retention_class"] = lane.get("retention_class")
            result[str(row["path"])] = row
    return result


def test_closeout_artifact_covers_requested_issues_5847_5852() -> None:
    payload = _load_json(CLOSEOUT)

    assert payload["schema_version"] == "tech-debt-issues-5847-5852-closeout-v1"
    assert payload["debt_budget_outcome"] == "reduced_or_unchanged"
    assert {issue["number"] for issue in payload["issues"]} == EXPECTED_ISSUES
    assert all(issue["status"] == "closed-ready" for issue in payload["issues"])
    for issue in payload["issues"]:
        for relative_path in issue["evidence"]:
            if relative_path in SUPERSEDED_IMAGE_PATHS:
                assert not (ROOT / relative_path).exists()
                continue
            assert (ROOT / relative_path).exists(), (
                f"Missing closeout evidence for #{issue['number']}: {relative_path}"
            )


def test_issue_5847_root_baseline_is_reduced_without_new_root_directory() -> None:
    payload = _load_json(CLOSEOUT)
    tracked = _git_ls_files()
    root_files = {path for path in tracked if "/" not in path}
    root_dirs = {path.split("/", maxsplit=1)[0] for path in tracked if "/" in path}
    allowlist_entries = {
        line.strip()
        for line in ROOT_ALLOWLIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    assert len(root_files) <= payload["outcomes"]["5847"]["tracked_root_files_after"]
    assert len(root_dirs) == payload["outcomes"]["5847"]["tracked_root_dirs_after"]
    assert len(allowlist_entries) <= payload["outcomes"]["5847"]["allowlist_entries_after"]
    assert not (RETIRED_ROOT_ENTRIES & tracked)
    for path in RETIRED_ROOT_ENTRIES:
        assert not (ROOT / path).exists()


def test_issue_5848_root_local_clutter_cleanup_command_is_bounded() -> None:
    payload = _load_json(CLOSEOUT)
    command_text = (
        ROOT / "scripts" / "engineering" / "repo" / "__main__.py"
    ).read_text(encoding="utf-8")
    script_text = (
        ROOT / "scripts" / "engineering" / "repo" / "cleanup_root_local_clutter.py"
    ).read_text(encoding="utf-8")

    assert payload["outcomes"]["5848"]["dry_run_default"] is True
    assert "cleanup-root-local-clutter" in command_text
    assert "SECURITY_ROOT_PATHS" in script_text
    assert "load_root_governance_policy" in script_text
    assert "--include-venv" in script_text
    structure_catalog = _load_yaml(
        ROOT / "configs" / "quality" / "repo_structure_catalog.yaml"
    )
    catalog_blocked_paths = {
        row["path"]
        for row in structure_catalog["blocked_cleanup_zones"]
        if isinstance(row, dict)
    }
    for blocked_path in payload["outcomes"]["5848"]["blocked_paths"]:
        if blocked_path.startswith(".env") or blocked_path == "new.env":
            assert blocked_path in script_text
        else:
            assert blocked_path in catalog_blocked_paths


def test_issue_5849_legacy_codex_root_aliases_are_retired() -> None:
    payload = _load_json(CLOSEOUT)
    tracked = _git_ls_files()
    candidates = _registry_candidates()
    allowlist_text = ROOT_ALLOWLIST.read_text(encoding="utf-8")

    expected_retired_shims = {
        ".wsl_proxy_env.sh": "scripts/engineering/dev/bash/.wsl_proxy_env.sh",
        "codex.bat": "scripts/ops/codex.bat",
        "codex.ps1": "scripts/ai/codex/run-codex.ps1",
        "run-codex.ps1": "scripts/ai/codex/run-codex.ps1",
        "run-codex-wsl.ps1": "scripts/ai/codex/run-codex.ps1",
        "setup-codex-wsl.bat": "scripts/ai/codex/setup-codex-wsl.bat",
        "setup-codex-wsl.ps1": "scripts/ai/codex/setup.ps1",
        "setup-codex-wsl.sh": "scripts/ai/codex/helper/setup-wsl-complete.sh",
    }
    assert set(payload["outcomes"]["5849"]["primary_root_shims"]) == set(
        expected_retired_shims
    )
    assert set(payload["outcomes"]["5849"]["retired_legacy_aliases"]) == set(
        expected_retired_shims
    )
    for path, canonical_path in expected_retired_shims.items():
        assert path not in tracked
        assert path not in allowlist_text
        assert candidates[path]["current_live_state"] == "absent_from_root_baseline"
        assert candidates[path]["canonical_path"] == canonical_path
        assert (ROOT / canonical_path).exists()


def test_issue_5850_compose_adjuncts_are_rehomed_and_contract_backed() -> None:
    payload = _load_json(CLOSEOUT)
    tracked = _git_ls_files()
    candidates = _registry_candidates()
    contracts = _load_yaml(DOCKER_CONTRACTS)
    allowlist_text = ROOT_ALLOWLIST.read_text(encoding="utf-8")
    makefile_text = (ROOT / "Makefile").read_text(encoding="utf-8")
    docker_docs_text = "\n".join(
        [
            (ROOT / "docs" / "DOCKER_SETUP.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "DOCKER_QUICKSTART.md").read_text(encoding="utf-8"),
        ]
    )

    assert payload["outcomes"]["5850"]["compose_rehome_map"] == COMPOSE_REHOME_MAP
    assert set(contracts["helpers"]) == set(COMPOSE_REHOME_MAP.values())
    for legacy_path, new_path in COMPOSE_REHOME_MAP.items():
        assert legacy_path not in tracked
        assert legacy_path not in allowlist_text
        assert new_path in tracked
        assert (ROOT / new_path).exists()
        assert (
            candidates[legacy_path]["current_live_state"] == "absent_from_root_baseline"
        )
        assert candidates[legacy_path]["canonical_path"] == new_path
        assert contracts["helpers"][new_path]["legacy_root_filename"] == legacy_path
        assert new_path in makefile_text or new_path in docker_docs_text


def test_issue_5851_helper_images_and_grafana_provisioning_are_rehomed() -> None:
    payload = _load_json(CLOSEOUT)
    tracked = _git_ls_files()
    candidates = _registry_candidates()
    root_compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert payload["outcomes"]["5851"]["image_rehome_map"] == IMAGE_REHOME_MAP
    for legacy_path, new_path in IMAGE_REHOME_MAP.items():
        assert legacy_path not in tracked
        if new_path in SUPERSEDED_IMAGE_PATHS:
            assert not (ROOT / new_path).exists()
            assert legacy_path not in candidates
        else:
            assert new_path in tracked
            assert (ROOT / new_path).exists()
            assert (
                candidates[legacy_path]["current_live_state"]
                == "absent_from_root_baseline"
            )
            assert candidates[legacy_path]["canonical_path"] == new_path

    assert "warp" not in root_compose.lower()
    assert not (ROOT / "docker-compose.codex.yml").exists()


def test_issue_5852_review_class_root_files_have_exact_filename_contracts() -> None:
    payload = _load_json(CLOSEOUT)
    candidates = _registry_candidates()
    expected = set(payload["outcomes"]["5852"]["exact_filename_contracts"])

    assert expected == {
        "best_practices.md",
        "commitlint.config.mjs",
        "mint.json",
    }
    assert (
        candidates["best_practices.md"]["lane_id"] == "root_reviewed_human_facing_docs"
    )
    for path in expected - {"best_practices.md"}:
        assert candidates[path]["lane_id"] == "root_review_contract_entrypoints"
        assert candidates[path]["owner"] == "Engineering / Review Tooling"
        assert (
            candidates[path]["retention_class"]
            == "reviewed_exact_filename_tool_contract"
        )
        assert candidates[path]["current_live_state"] == "present_approved_root_surface"
    assert candidates["pr_compliance_checklist.yaml"]["current_live_state"] == "absent_from_root_baseline"
    assert candidates["pr_compliance_checklist.yaml"]["canonical_path"] is None
