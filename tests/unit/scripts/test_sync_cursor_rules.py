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
"""Unit tests for Cursor rules and project-command deploy sync."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

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


def test_canonical_cursor_rules_declare_apply_mode() -> None:
    """File-scoped rules must set alwaysApply and quoted globs for Windsurf sync."""
    root = Path(__file__).resolve().parents[3]
    rules = sorted((root / "docs/00-project/ai/rules/cursor").glob("*.mdc"))
    assert rules
    for path in rules:
        if path.name == "sonarqube_mcp_instructions.mdc":
            continue
        text = path.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        assert len(parts) >= 3, path.name
        meta = yaml.safe_load(parts[1])
        assert isinstance(meta, dict), path.name
        assert "alwaysApply" in meta, path.name
        assert isinstance(meta["alwaysApply"], bool), path.name
        if meta["alwaysApply"] is True:
            continue
        globs = meta.get("globs")
        assert isinstance(globs, list) and globs, path.name
        assert all(isinstance(pattern, str) and pattern for pattern in globs), path.name


def _write_command(path: Path, name: str, *, body: str | None = None) -> None:
    path.mkdir(parents=True, exist_ok=True)
    payload = body
    if payload is None:
        tokens = "\n".join(
            f"- {token}" for token in sync_cursor_rules.COMMAND_GOVERNANCE_TOKENS
        )
        marker = sync_cursor_rules.MANAGED_COMMAND_MARKER
        payload = f"---\ndescription: test\n---\n\n{tokens}\n\n{marker}\n"
    (path / name).write_text(payload, encoding="utf-8", newline="\n")


def test_sync_cursor_commands_deploy_copies_canonical_files(tmp_path: Path) -> None:
    canonical = tmp_path / sync_cursor_rules.CURSOR_COMMAND_DOCS_DIR
    _write_command(canonical, "review.md")

    issues = sync_cursor_rules.sync_cursor_commands(
        root=tmp_path,
        deploy=True,
        check_only=False,
    )

    assert issues == []
    deployed = tmp_path / sync_cursor_rules.CURSOR_COMMANDS_DIR / "review.md"
    assert deployed.read_text(encoding="utf-8") == (canonical / "review.md").read_text(
        encoding="utf-8"
    )


def test_sync_cursor_commands_check_reports_missing_deploy(tmp_path: Path) -> None:
    canonical = tmp_path / sync_cursor_rules.CURSOR_COMMAND_DOCS_DIR
    _write_command(canonical, "review.md")

    issues = sync_cursor_rules.sync_cursor_commands(
        root=tmp_path,
        deploy=False,
        check_only=True,
    )

    assert any("missing" in issue for issue in issues)


def test_sync_cursor_commands_check_reports_out_of_sync(tmp_path: Path) -> None:
    canonical = tmp_path / sync_cursor_rules.CURSOR_COMMAND_DOCS_DIR
    deploy = tmp_path / sync_cursor_rules.CURSOR_COMMANDS_DIR
    _write_command(canonical, "review.md")
    _write_command(deploy, "review.md", body="---\ndescription: stale\n---\n")

    issues = sync_cursor_rules.sync_cursor_commands(
        root=tmp_path,
        deploy=False,
        check_only=True,
    )

    assert any("out of sync" in issue for issue in issues)


def test_sync_cursor_commands_check_reports_orphan(tmp_path: Path) -> None:
    canonical = tmp_path / sync_cursor_rules.CURSOR_COMMAND_DOCS_DIR
    deploy = tmp_path / sync_cursor_rules.CURSOR_COMMANDS_DIR
    _write_command(canonical, "review.md")
    _write_command(deploy, "review.md")
    _write_command(deploy, "local-only.md")

    issues = sync_cursor_rules.sync_cursor_commands(
        root=tmp_path,
        deploy=False,
        check_only=True,
    )

    assert any(
        "orphan deploy file" in issue and "local-only.md" in issue for issue in issues
    )


def test_sync_cursor_commands_deploy_removes_orphan(tmp_path: Path) -> None:
    canonical = tmp_path / sync_cursor_rules.CURSOR_COMMAND_DOCS_DIR
    deploy = tmp_path / sync_cursor_rules.CURSOR_COMMANDS_DIR
    _write_command(canonical, "review.md")
    _write_command(deploy, "review.md")
    _write_command(deploy, "old-review.md")

    issues = sync_cursor_rules.sync_cursor_commands(
        root=tmp_path,
        deploy=True,
        check_only=False,
    )

    assert issues == []
    assert (deploy / "review.md").is_file()
    assert not (deploy / "old-review.md").exists()


def test_sync_cursor_commands_deploy_removes_copy_failing_token_check(
    tmp_path: Path,
) -> None:
    canonical = tmp_path / sync_cursor_rules.CURSOR_COMMAND_DOCS_DIR
    deploy = tmp_path / sync_cursor_rules.CURSOR_COMMANDS_DIR
    _write_command(canonical, "review.md")
    _write_command(canonical, "bare.md", body="---\ndescription: bare\n---\n\n# bare\n")
    _write_command(deploy, "bare.md")

    issues = sync_cursor_rules.sync_cursor_commands(
        root=tmp_path,
        deploy=True,
        check_only=False,
    )

    assert any(
        "bare.md" in issue and "missing governance token" in issue for issue in issues
    )
    assert (deploy / "review.md").is_file()
    assert not (deploy / "bare.md").exists()


def test_sync_cursor_commands_skips_file_missing_governance_token(
    tmp_path: Path,
) -> None:
    canonical = tmp_path / sync_cursor_rules.CURSOR_COMMAND_DOCS_DIR
    _write_command(canonical, "review.md")
    _write_command(canonical, "bare.md", body="---\ndescription: bare\n---\n\n# bare\n")

    issues = sync_cursor_rules.sync_cursor_commands(
        root=tmp_path,
        deploy=True,
        check_only=False,
    )

    deploy = tmp_path / sync_cursor_rules.CURSOR_COMMANDS_DIR
    assert any(
        "bare.md" in issue and "missing governance token" in issue for issue in issues
    )
    assert (deploy / "review.md").is_file()
    assert not (deploy / "bare.md").exists()


def test_deploy_prunes_stale_managed_commands_and_preserves_local_files(
    tmp_path: Path,
) -> None:
    canonical = tmp_path / sync_cursor_rules.CURSOR_COMMAND_DOCS_DIR
    deploy = tmp_path / sync_cursor_rules.CURSOR_COMMANDS_DIR
    _write_command(canonical, "old.md")
    _write_command(canonical, "invalid.md")
    assert not sync_cursor_rules.sync_cursor_commands(
        root=tmp_path, deploy=True, check_only=False
    )
    (canonical / "old.md").rename(canonical / "renamed.md")
    _write_command(canonical, "invalid.md", body="Invalid command")
    _write_command(deploy, "local.md", body="Personal command")
    _write_command(canonical, "local.md")

    issues = sync_cursor_rules.sync_cursor_commands(
        root=tmp_path, deploy=True, check_only=False
    )

    assert any("invalid.md" in issue for issue in issues)
    assert any("unmarked local command preserved" in issue for issue in issues)
    assert (deploy / "renamed.md").is_file()
    assert not (deploy / "old.md").exists()
    assert not (deploy / "invalid.md").exists()
    assert (deploy / "local.md").read_text(encoding="utf-8") == "Personal command"


def test_canonical_cursor_commands_include_governance_tokens() -> None:
    root = Path(__file__).resolve().parents[3]
    commands = sorted((root / sync_cursor_rules.CURSOR_COMMAND_DOCS_DIR).glob("*.md"))
    assert [path.name for path in commands] == [
        "post-change.md",
        "pre-commit.md",
        "qodo-sync.md",
        "review.md",
    ]
    for path in commands:
        text = path.read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        assert "auto_execution_mode" not in frontmatter
        for token in sync_cursor_rules.COMMAND_GOVERNANCE_TOKENS:
            assert token in text, path.name


def test_main_defaults_to_check(tmp_path: Path) -> None:
    """Bare CLI must not deploy into .cursor/rules (#9119)."""
    canonical = tmp_path / sync_cursor_rules.CURSOR_RULE_DOCS_DIR
    _write_rule(canonical, "00-test.mdc", "# Canonical\n")
    deploy = tmp_path / sync_cursor_rules.CURSOR_RULES_DIR

    exit_code = sync_cursor_rules.main(["--root", str(tmp_path)])

    assert exit_code == 1
    assert not deploy.exists()
