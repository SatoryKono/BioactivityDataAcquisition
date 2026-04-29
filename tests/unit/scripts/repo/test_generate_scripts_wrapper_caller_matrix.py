"""Unit tests for the scripts wrapper caller matrix generator."""

from __future__ import annotations

from scripts.engineering.repo import generate_scripts_wrapper_caller_matrix as module


def test_render_report_lists_known_wrapper_candidates() -> None:
    report = module._render_report(module._project_root())

    assert "# Scripts CLI Wrapper Caller Matrix" in report
    assert "`scripts/docs/build_docs_site.sh`" in report
    assert "`scripts/ops/launchers/codex/codex.sh`" in report
    assert "retain" in report
