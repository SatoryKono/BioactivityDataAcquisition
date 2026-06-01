"""Architecture tests for active runtime docs mirror and freshness guardrails."""

from __future__ import annotations

import pytest

import importlib
from types import ModuleType


pytestmark = pytest.mark.architecture

def _load_doc_drift_module() -> ModuleType:
    return importlib.import_module("scripts.docs.checks.check_drift")


def _issues_to_text(report: object) -> str:
    issues = report.issues
    return "\n".join(
        f"{issue.category}::{issue.doc_file}::{issue.detail}" for issue in issues
    )


def test_runtime_agent_mirror_drift_check_passes_current_repo() -> None:
    mod = _load_doc_drift_module()
    report = mod.DriftReport()
    mod.check_runtime_mirrors(report)

    assert not report.issues, (
        "Critical runtime docs mirrors drifted from canonical .codex sources.\n"
        f"{_issues_to_text(report)}"
    )


def test_runtime_doc_freshness_check_passes_current_repo() -> None:
    mod = _load_doc_drift_module()
    report = mod.DriftReport()
    mod.check_freshness(report)

    assert not report.error_count, (
        "Active runtime/governance docs contain freshness or version drift.\n"
        f"{_issues_to_text(report)}"
    )
