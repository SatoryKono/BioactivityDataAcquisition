"""Architecture tests for AI runtime governance link coverage and drift."""

from __future__ import annotations

import importlib
from types import ModuleType

import pytest


pytestmark = pytest.mark.architecture


def _load_doc_drift_module() -> ModuleType:
    return importlib.import_module("scripts.docs.checks.check_drift")


def _issues_to_text(report: object) -> str:
    issues = report.issues
    return "\n".join(
        f"{issue.category}::{issue.doc_file}::{issue.detail}" for issue in issues
    )


def test_ai_runtime_governance_link_check_passes_current_repo() -> None:
    mod = _load_doc_drift_module()
    report = mod.DriftReport()
    mod.check_ai_surfaces(report)

    assert not report.issues, (
        "AI runtime governance surfaces drifted from canonical policy requirements.\n"
        f"{_issues_to_text(report)}"
    )
