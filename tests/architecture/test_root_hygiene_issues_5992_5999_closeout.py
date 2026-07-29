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


def test_issue_5994_root_codex_shims_are_retired_to_canonical_owners() -> None:
    retired_root_shims = {
        ".wsl_proxy_env.sh": "scripts/engineering/dev/bash/.wsl_proxy_env.sh",
        "codex.bat": "scripts/ops/codex.bat",
        "codex.ps1": "scripts/ai/codex/run-codex.ps1",
        "run-codex.ps1": "scripts/ai/codex/run-codex.ps1",
        "run-codex-wsl.ps1": "scripts/ai/codex/run-codex.ps1",
        "setup-codex-wsl.bat": "scripts/ai/codex/setup-codex-wsl.bat",
        "setup-codex-wsl.ps1": "scripts/ai/codex/setup.ps1",
        "setup-codex-wsl.sh": "scripts/ai/codex/helper/setup-wsl-complete.sh",
    }

    for root_shim, canonical_owner in retired_root_shims.items():
        assert not (ROOT / root_shim).exists()
        assert (ROOT / canonical_owner).exists()

    readme = _read("scripts/ai/codex/README.md")
    assert "Retired Root Shim Verification" in readme
    assert "root hygiene issue #5994" in readme
    assert "#6152-#6158" in readme


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

    assert not (ROOT / "docker-setup.ps1").exists()
    assert not (ROOT / "docker-setup.sh").exists()
    assert (ROOT / "scripts/ops/docker-setup.ps1").exists()
    assert (ROOT / "scripts/ops/docker-setup.sh").exists()
    assert "Reference Map Verification" in audit
    assert "root hygiene issues #5995 and #6725" in audit
    assert "Last verified: 2026-07-27" in audit
    assert "retired root script" in audit
    assert "RF-003 Command Compatibility Matrix" in audit


def test_issue_5999_exact_root_review_tooling_has_retention_decisions() -> None:
    qodo_readme = _read("docs/00-project/governance/qodo/README.md")

    for root_surface in (
        ".pr_agent.toml",
        "best_practices.md",
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


def test_issue_6725_local_root_context_and_backup_have_cleanup_guidance() -> None:
    cleanup_guide = _read("docs/00-project/governance/root-local-clutter-cleanup.md")

    assert ".mcp-server-context.md" in cleanup_guide
    assert "Keep while an active MCP client uses it" in cleanup_guide
    assert "MUST NOT be promoted to a tracked source of truth" in cleanup_guide
    assert ".gitignore~" in cleanup_guide
    assert "safe to delete" in cleanup_guide
