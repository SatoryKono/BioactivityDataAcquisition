"""P1 #9808 — guard_non_weakening + no_controller_duplication (DOCX гл.4.3)."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.ai.prompts.lint import LintReport, check_overlay

import pytest

pytestmark = pytest.mark.unit


def _base_overlay() -> dict:
    return {
        "domain": "test-guard",
        "id": "prompt.audit.cycle.test-guard",
        "OBJECT": "test object",
        "SCOPE": ["src/test"],
    }


def _lint(data: dict, raw_extra: str = "") -> LintReport:
    report = LintReport()
    raw = yaml.safe_dump(data) + raw_extra
    check_overlay(report, Path("overlays/test-guard.yaml"), data, raw)
    return report


def test_overlay_allow_true_triggers_guard_non_weakening() -> None:
    data = _base_overlay()
    data["ALLOW_ISSUE_WRITE"] = True  # type: ignore[assignment]
    report = _lint(data, "\nALLOW_ISSUE_WRITE: true\n")
    codes = [e.code for e in report.errors]
    assert "guard_non_weakening" in codes


def test_overlay_controller_phrase_triggers_no_controller_duplication() -> None:
    data = _base_overlay()
    data["AUDIT_CONTOURS"] = ["Scope freeze the plan before audit"]  # controller phrase
    report = _lint(data)
    codes = [e.code for e in report.errors]
    assert "no_controller_duplication" in codes


def test_valid_overlay_clean() -> None:
    data = _base_overlay()
    data["SSOT"] = ["docs/00-project/RULES.md"]
    data["AUDIT_CONTOURS"] = ["check freshness of SSOT links"]
    report = _lint(data)
    guard = [e for e in report.errors if e.code in ("guard_non_weakening", "no_controller_duplication")]
    assert guard == [], f"valid overlay must not trigger guards: {guard}"
