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
"""Unit tests for Cursor rules deploy sync."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ai.sync import cursor as sync_cursor_rules

pytestmark = pytest.mark.unit


def _write_rule(path: Path, name: str, body: str = "# Rule\n") -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / name).write_text(
        f"---\ndescription: test\n---\n\n{body}",
        encoding="utf-8",
    )


def test_sync_cursor_rules_deploy_copies_canonical_files(tmp_path: Path) -> None:
    canonical = tmp_path / sync_cursor_rules.CURSOR_RULE_DOCS_DIR
    _write_rule(canonical, "00-test.mdc", "# Canonical\n")

    issues = sync_cursor_rules.sync_cursor_rules(
        root=tmp_path,
        deploy=True,
        check_only=False,
    )

    assert issues == []
    deployed = tmp_path / sync_cursor_rules.CURSOR_RULES_DIR / "00-test.mdc"
    assert deployed.read_text(encoding="utf-8") == (
        canonical / "00-test.mdc"
    ).read_text(encoding="utf-8")


def test_sync_cursor_rules_check_reports_missing_deploy(tmp_path: Path) -> None:
    canonical = tmp_path / sync_cursor_rules.CURSOR_RULE_DOCS_DIR
    _write_rule(canonical, "00-test.mdc")

    issues = sync_cursor_rules.sync_cursor_rules(
        root=tmp_path,
        deploy=False,
        check_only=True,
    )

    assert any("missing" in issue for issue in issues)


def test_sync_cursor_rules_check_reports_out_of_sync(tmp_path: Path) -> None:
    canonical = tmp_path / sync_cursor_rules.CURSOR_RULE_DOCS_DIR
    deploy = tmp_path / sync_cursor_rules.CURSOR_RULES_DIR
    _write_rule(canonical, "00-test.mdc", "# Canonical\n")
    _write_rule(deploy, "00-test.mdc", "# Stale\n")

    issues = sync_cursor_rules.sync_cursor_rules(
        root=tmp_path,
        deploy=False,
        check_only=True,
    )

    assert any("out of sync" in issue for issue in issues)


def test_sync_cursor_rules_excludes_sonarqube_instructions(tmp_path: Path) -> None:
    canonical = tmp_path / sync_cursor_rules.CURSOR_RULE_DOCS_DIR
    _write_rule(canonical, "sonarqube_mcp_instructions.mdc")
    _write_rule(canonical, "00-test.mdc")

    issues = sync_cursor_rules.sync_cursor_rules(
        root=tmp_path,
        deploy=True,
        check_only=False,
    )

    assert issues == []
    deploy = tmp_path / sync_cursor_rules.CURSOR_RULES_DIR
    assert (deploy / "00-test.mdc").exists()
    assert not (deploy / "sonarqube_mcp_instructions.mdc").exists()
