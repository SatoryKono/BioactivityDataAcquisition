"""Unit tests for AI-surface drift checks."""

from __future__ import annotations

from pathlib import Path

from scripts.docs.checks import check_drift


def test_check_ai_surfaces_reports_missing_policy_token(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_text("root contract without policy links\n", encoding="utf-8")

    monkeypatch.setattr(
        check_drift,
        "AI_SURFACE_REQUIRED_TOKENS",
        {Path("AGENTS.md"): ("MEMORY_USAGE.md",)},
    )
    monkeypatch.setattr(check_drift, "AI_SURFACE_STALE_PATTERNS", ())
    monkeypatch.setattr(check_drift, "AI_SURFACE_FORBIDDEN_PATTERNS", {})

    report = check_drift.DriftReport()
    check_drift.check_ai_surfaces(report, root=tmp_path)

    assert report.error_count == 1
    assert "Missing required AI policy/runtime token" in report.issues[0].detail


def test_check_ai_surfaces_reports_forbidden_legacy_runtime_dependency(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / ".gemini" / "skills" / "new-pipeline" / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "Primary instructions: ../../../.claude/skills/new-pipeline.md\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(check_drift, "AI_SURFACE_REQUIRED_TOKENS", {})
    monkeypatch.setattr(check_drift, "AI_SURFACE_STALE_PATTERNS", ())
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
