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
"""Unit tests for AI-surface drift checks."""

from __future__ import annotations

import pytest

from pathlib import Path

from scripts.docs.checks import check_drift


pytestmark = pytest.mark.unit


def _disable_all_ai_surface_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Helper to disable all AI surface checks except the one being tested."""
    monkeypatch.setattr(check_drift, "AI_SURFACE_REQUIRED_TOKENS", {})
    monkeypatch.setattr(check_drift, "AI_WRITE_CAPABLE_SKILL_REQUIRED_TOKENS", {})
    monkeypatch.setattr(check_drift, "AI_ROLE_PROFILE_REQUIRED_TOKENS", {})
    monkeypatch.setattr(check_drift, "AI_ROLE_MEMORY_COVERAGE_REQUIRED_TOKENS", {})
    monkeypatch.setattr(check_drift, "AI_MIRROR_NOTICE_REQUIRED_TOKENS", {})
    monkeypatch.setattr(check_drift, "AI_SURFACE_STALE_PATTERNS", ())
    monkeypatch.setattr(check_drift, "AI_RULES_MIRROR_REQUIRED_TOKENS", {})
    monkeypatch.setattr(check_drift, "AI_GEMINI_RUNTIME_CLAIM_GUARD_PATHS", ())
    monkeypatch.setattr(check_drift, "_iter_cursor_rule_entrypoints", lambda _: ())
    monkeypatch.setattr(check_drift, "_iter_runtime_skill_entrypoints", lambda _: ())
    monkeypatch.setattr(check_drift, "AI_SURFACE_FORBIDDEN_PATTERNS", {})


def test_check_modules_allows_governed_tracing_attributes(
    monkeypatch, tmp_path: Path
) -> None:
    docs_dir = tmp_path / "docs"
    arch_dir = docs_dir / "02-architecture"
    arch_dir.mkdir(parents=True)
    (arch_dir / "observability-layers.md").write_text(
        "`bioetl.provider`\n`bioetl.run_id`\n", encoding="utf-8"
    )

    src_dir = tmp_path / "src" / "bioetl"
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text("", encoding="utf-8")

    tracing_config = tmp_path / "configs" / "quality" / "mandatory_tracing.yaml"
    tracing_config.parent.mkdir(parents=True)
    tracing_config.write_text(
        """
surfaces:
  adapter_request:
    files:
      - path: src/bioetl/infrastructure/adapters/http/client_retry_observability.py
        required_terms:
          - bioetl.provider
          - bioetl.run_id
""".lstrip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(check_drift, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(check_drift, "DOCS_DIR", docs_dir)
    monkeypatch.setattr(check_drift, "SRC_DIR", src_dir)
    monkeypatch.setattr(check_drift, "MANDATORY_TRACING_COVERAGE_PATH", tracing_config)

    report = check_drift.DriftReport()
    check_drift.check_modules(report)

    assert report.issues == []


def test_check_modules_still_reports_unknown_bioetl_module(
    monkeypatch, tmp_path: Path
) -> None:
    docs_dir = tmp_path / "docs"
    arch_dir = docs_dir / "02-architecture"
    arch_dir.mkdir(parents=True)
    (arch_dir / "overview.md").write_text("`bioetl.missing_module`\n", encoding="utf-8")

    src_dir = tmp_path / "src" / "bioetl"
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text("", encoding="utf-8")

    tracing_config = tmp_path / "configs" / "quality" / "mandatory_tracing.yaml"
    tracing_config.parent.mkdir(parents=True)
    tracing_config.write_text("surfaces: {}\n", encoding="utf-8")

    monkeypatch.setattr(check_drift, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(check_drift, "DOCS_DIR", docs_dir)
    monkeypatch.setattr(check_drift, "SRC_DIR", src_dir)
    monkeypatch.setattr(check_drift, "MANDATORY_TRACING_COVERAGE_PATH", tracing_config)

    report = check_drift.DriftReport()
    check_drift.check_modules(report)

    assert report.error_count == 1
    assert "bioetl.missing_module" in report.issues[0].detail


def test_check_ai_surfaces_reports_missing_policy_token(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_text("root contract without policy links\n", encoding="utf-8")

    _disable_all_ai_surface_checks(monkeypatch)
    monkeypatch.setattr(
        check_drift,
        "AI_SURFACE_REQUIRED_TOKENS",
        {Path("AGENTS.md"): ("MEMORY_USAGE.md",)},
    )

    report = check_drift.DriftReport()
    check_drift.check_ai_surfaces(report, root=tmp_path)

    assert report.error_count == 1
    assert "Missing required AI policy/runtime token" in report.issues[0].detail


def test_gemini_claim_guard_allows_missing_machine_local_cursor_deploy(
    tmp_path: Path,
) -> None:
    canonical = (
        tmp_path
        / "docs"
        / "00-project"
        / "ai"
        / "rules"
        / "cursor"
        / "05-agent-workflow.mdc"
    )
    canonical.parent.mkdir(parents=True)
    canonical.write_text("canonical Cursor rule\n", encoding="utf-8")

    report = check_drift.DriftReport()
    check_drift._check_unverified_gemini_runtime_claims(
        report,
        project_root=tmp_path,
    )

    missing_paths = {issue.doc_file for issue in report.issues}
    assert ".cursor/rules/05-agent-workflow.mdc" not in missing_paths


def test_check_ai_surfaces_reports_forbidden_legacy_runtime_dependency(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / ".gemini" / "skills" / "new-pipeline" / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "Primary instructions: ../../../.claude/skills/new-pipeline.md\n",
        encoding="utf-8",
    )

    _disable_all_ai_surface_checks(monkeypatch)
    monkeypatch.setattr(
        check_drift,
        "AI_SURFACE_FORBIDDEN_PATTERNS",
        {
            Path(".gemini/skills/new-pipeline/SKILL.md"): (
                check_drift.re.compile(r"\.claude/"),
            )
        },
    )

    report = check_drift.DriftReport()
    check_drift.check_ai_surfaces(report, root=tmp_path)

    assert report.error_count == 1
    assert "Forbidden legacy runtime dependency detected" in report.issues[0].detail


def test_check_ai_surfaces_reports_write_capable_skill_without_post_change_policy(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / ".codex" / "skills" / "create-pr" / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "Project runtime contract: ../../../AGENTS.md\n", encoding="utf-8"
    )

    _disable_all_ai_surface_checks(monkeypatch)
    monkeypatch.setattr(
        check_drift,
        "AI_WRITE_CAPABLE_SKILL_REQUIRED_TOKENS",
        {
            Path(".codex/skills/create-pr/SKILL.md"): (
                "AGENTS.md",
                "MEMORY_USAGE.md",
                "POST_CHANGE_VALIDATION.md",
            )
        },
    )

    report = check_drift.DriftReport()
    check_drift.check_ai_surfaces(report, root=tmp_path)

    assert report.error_count == 2
    assert {issue.detail for issue in report.issues} == {
        "Missing required AI policy/runtime token: MEMORY_USAGE.md",
        "Missing required AI policy/runtime token: POST_CHANGE_VALIDATION.md",
    }


def test_check_ai_surfaces_reports_docs_mirror_without_non_canonical_notice(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "docs" / "00-project" / "ai" / "skills" / "README.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "Skills catalog without mirror ownership notice\n", encoding="utf-8"
    )

    _disable_all_ai_surface_checks(monkeypatch)
    monkeypatch.setattr(
        check_drift,
        "AI_MIRROR_NOTICE_REQUIRED_TOKENS",
        {
            Path("docs/00-project/ai/skills/README.md"): (
                "Non-Canonical Mirror Notice",
                ".codex/skills/**",
            )
        },
    )

    report = check_drift.DriftReport()
    check_drift.check_ai_surfaces(report, root=tmp_path)

    assert report.error_count == 2
    assert {issue.detail for issue in report.issues} == {
        "Missing required AI policy/runtime token: Non-Canonical Mirror Notice",
        "Missing required AI policy/runtime token: .codex/skills/**",
    }


def test_check_ai_surfaces_reports_agent_mirror_without_runtime_header(
    monkeypatch, tmp_path: Path
) -> None:
    target = (
        tmp_path
        / "docs"
        / "00-project"
        / "ai"
        / "agents"
        / "agents"
        / "py-audit-bot.md"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "# py-audit-bot\n\nMirror body without source notice\n", encoding="utf-8"
    )

    codex_runtime = tmp_path / ".codex" / "agents" / "py-audit-bot.md"
    codex_runtime.parent.mkdir(parents=True, exist_ok=True)
    codex_runtime.write_text("# runtime\n", encoding="utf-8")

    gemini_runtime = tmp_path / ".gemini" / "agents" / "py-audit-bot.md"
    gemini_runtime.parent.mkdir(parents=True, exist_ok=True)
    gemini_runtime.write_text("# runtime\n", encoding="utf-8")

    _disable_all_ai_surface_checks(monkeypatch)

    report = check_drift.DriftReport()
    check_drift.check_ai_surfaces(report, root=tmp_path)

    assert report.error_count == 5
    assert {
        issue.detail
        for issue in report.issues
        if issue.doc_file == "docs/00-project/ai/agents/agents/py-audit-bot.md"
    } == {
        "AI docs mirror header missing required token in first section: Mirror status:",
        "AI docs mirror header missing required token in first section: not a canonical runtime surface",
        "AI docs mirror header missing required token in first section: AI_RUNTIME_MIRROR_OWNERSHIP.md",
        "AI docs mirror header missing canonical runtime source: .codex/agents/py-audit-bot.md",
        "AI docs mirror header missing canonical runtime source: .gemini/agents/py-audit-bot.md",
    }


def test_check_ai_surfaces_accepts_skill_mirror_with_runtime_header(
    monkeypatch, tmp_path: Path
) -> None:
    target = (
        tmp_path
        / "docs"
        / "00-project"
        / "ai"
        / "skills"
        / "local"
        / "create-pr"
        / "SKILL.md"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(
            [
                "> Mirror status: This file is a published/internal mirror.",
                "> It is not a canonical runtime surface.",
                "> Canonical runtime source: `.codex/skills/create-pr/SKILL.md`",
                "> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md",
                "",
                "# create-pr",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    runtime = tmp_path / ".codex" / "skills" / "create-pr" / "SKILL.md"
    runtime.parent.mkdir(parents=True, exist_ok=True)
    runtime.write_text("# runtime\n", encoding="utf-8")

    _disable_all_ai_surface_checks(monkeypatch)

    report = check_drift.DriftReport()
    check_drift.check_ai_surfaces(report, root=tmp_path)

    assert not [
        issue
        for issue in report.issues
        if issue.doc_file == "docs/00-project/ai/skills/local/create-pr/SKILL.md"
    ]


def test_check_ai_surfaces_reports_missing_role_profile_post_change_anchor(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / ".codex" / "agents" / "py-config-bot.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(
            [
                "Memory policy: docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
                "Project memory: docs/00-project/ai/memory/agent-memory.md",
                "Role memory: docs/00-project/ai/memory/memory-py-config-bot.md",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    _disable_all_ai_surface_checks(monkeypatch)
    monkeypatch.setattr(
        check_drift,
        "AI_ROLE_PROFILE_REQUIRED_TOKENS",
        {
            Path(".codex/agents/py-config-bot.md"): (
                "MEMORY_USAGE.md",
                "agent-memory.md",
                "memory-py-config-bot.md",
                "POST_CHANGE_VALIDATION.md",
            )
        },
    )

    report = check_drift.DriftReport()
    check_drift.check_ai_surfaces(report, root=tmp_path)

    assert report.error_count == 1
    assert report.issues[0].doc_file == ".codex/agents/py-config-bot.md"
    assert report.issues[0].detail.endswith("POST_CHANGE_VALIDATION.md")


def test_check_ai_surfaces_reports_missing_specialized_role_memory_coverage(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "docs" / "00-project" / "ai" / "memory" / "README.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "Role matrix without specialized orchestrator memory rows\n",
        encoding="utf-8",
    )

    _disable_all_ai_surface_checks(monkeypatch)
    monkeypatch.setattr(
        check_drift,
        "AI_ROLE_MEMORY_COVERAGE_REQUIRED_TOKENS",
        {
            Path("docs/00-project/ai/memory/README.md"): (
                "memory-py-audit-bot.md",
                "memory-py-test-bot.md",
                "memory-py-doc-bot.md",
            )
        },
    )

    report = check_drift.DriftReport()
    check_drift.check_ai_surfaces(report, root=tmp_path)

    assert report.error_count == 3
    assert {issue.detail for issue in report.issues} == {
        "Missing required AI policy/runtime token: memory-py-audit-bot.md",
        "Missing required AI policy/runtime token: memory-py-test-bot.md",
        "Missing required AI policy/runtime token: memory-py-doc-bot.md",
    }


def test_check_stale_rules_version_literals_flags_outdated_marker(
    monkeypatch, tmp_path: Path
) -> None:
    rules = tmp_path / "docs" / "00-project" / "RULES.md"
    rules.parent.mkdir(parents=True)
    rules.write_text("Version: 6.1.4\n", encoding="utf-8")

    target = tmp_path / "docs" / "00-project" / "00-map.md"
    target.write_text("Synced with RULES.md v6.1.3\n", encoding="utf-8")

    monkeypatch.setattr(check_drift, "PROJECT_ROOT", tmp_path)

    report = check_drift.DriftReport()
    check_drift._check_stale_rules_version_literals(report, project_root=tmp_path)

    assert report.error_count == 1
    assert "Stale RULES.md version literal" in report.issues[0].detail


def test_check_cursor_rule_entrypoints_reports_missing_normative_tokens(
    tmp_path: Path,
) -> None:
    canonical = tmp_path / check_drift.CURSOR_RULE_DOCS_DIR
    canonical.mkdir(parents=True)
    (canonical / "00-test.mdc").write_text(
        "---\ndescription: test\n---\n\n# Rule\n",
        encoding="utf-8",
    )

    report = check_drift.DriftReport()
    check_drift._check_cursor_rule_entrypoints(report, project_root=tmp_path)

    assert report.error_count == 5
    assert {issue.detail for issue in report.issues} == {
        "Missing required AI policy/runtime token: AGENTS.md",
        "Missing required AI policy/runtime token: docs/00-project/NORMATIVE_SOURCES.md",
        "Missing required AI policy/runtime token: docs/00-project/RULES.md",
        "Missing required AI policy/runtime token: docs/01-requirements/REQUIREMENTS.md",
        "Missing required AI policy/runtime token: docs/02-architecture/decisions/",
    }
