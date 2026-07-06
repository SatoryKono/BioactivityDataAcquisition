"""Closeout guards for root hygiene issues #5992, #5993, #5994, #5995, #5999."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_issue_5992_local_root_blockers_are_absent() -> None:
    blocked_root_artifacts = {
        "_agent_5671_fix_diag.py",
        "_tmp_parse_issues.py",
        "temp_create_audit.py",
        ".venv-new",
        "path",
        "silver",
    }

    present = sorted(
        artifact for artifact in blocked_root_artifacts if (ROOT / artifact).exists()
    )

    assert present == []


def test_issue_5993_generated_output_routing_keeps_forbidden_root_outputs() -> None:
    payload = yaml.safe_load(
        (ROOT / "configs/quality/generated_artifact_routing.yaml").read_text(
            encoding="utf-8",
        )
    )

    forbidden_roots = set(payload["forbidden_output_roots"])

    assert {"logs/", "test-output/", "silver/", "caddy/"} <= forbidden_roots
    assert payload["allowed_output_roots"]["working_reports"] == ["reports/"]


def test_issue_5994_root_codex_shims_delegate_to_canonical_owners() -> None:
    expected_delegates = {
        "codex.ps1": "scripts\\ai\\codex\\run-codex.ps1",
        "codex.bat": "codex.ps1",
        "setup-codex-wsl.bat": "scripts\\ai\\codex\\setup-codex-wsl.bat",
        "setup-codex-wsl.ps1": "scripts\\ai\\codex\\setup-codex-wsl.bat",
        "setup-codex-wsl.sh": "scripts/ai/codex/helper/setup-wsl-complete.sh",
        ".wsl_proxy_env.sh": "scripts/ai/codex/helper/wsl_proxy_env.sh",
    }

    for root_shim, canonical_owner in expected_delegates.items():
        assert canonical_owner in _read(root_shim)

    assert not (ROOT / "run-codex.ps1").exists()
    assert not (ROOT / "run-codex-wsl.ps1").exists()

    readme = _read("scripts/ai/codex/README.md")
    assert "Root Shim Verification" in readme
    assert "root hygiene issue #5994" in readme


def test_issue_5995_docker_root_entrypoints_have_reference_map() -> None:
    audit = _read(
        "docs/05-operations/verification/docker-helper-root-relocation-audit.md"
    )

    for root_surface in (
        "Dockerfile.bioetl",
        "docker-compose.yml",
        "docker-compose.monitoring.yml",
        "docker-compose.codex.yml",
        "docker-compose.neo4j.yml",
        "docker-compose.neo4j-audit.yml",
        "docker-setup.ps1",
        "docker-setup.sh",
    ):
        assert root_surface in audit

    assert "Reference Map Verification" in audit
    assert "root hygiene issue #5995" in audit
    assert "wrapper-first migration" in audit


def test_issue_5999_exact_root_review_tooling_has_retention_decisions() -> None:
    qodo_readme = _read("docs/00-project/governance/qodo/README.md")

    for root_surface in (
        ".pr_agent.toml",
        "best_practices.md",
        "pr_compliance_checklist.yaml",
        "commitlint.config.mjs",
        "mint.json",
    ):
        assert root_surface in qodo_readme

    assert "Root Retention Revalidation" in qodo_readme
    assert "root hygiene issue #5999" in qodo_readme
    assert (
        "No root review/tooling file should move based only on naming preference"
        in (qodo_readme)
    )
